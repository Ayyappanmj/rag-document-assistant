"""Orchestrates document processing: extract -> chunk -> embed -> index."""
import logging
import threading
import time
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.models.database import Document, DocumentChunk
from app.rag import dependencies as deps
from app.rag.chunker import Chunker
from app.rag.document_processor import DocumentProcessor, PDFExtractionError

logger = logging.getLogger(__name__)

_ACTIVE_JOBS: set[str] = set()
_ACTIVE_LOCK = threading.Lock()


def mark_job_started(doc_id: str) -> None:
    with _ACTIVE_LOCK:
        _ACTIVE_JOBS.add(doc_id)


def mark_job_finished(doc_id: str) -> None:
    with _ACTIVE_LOCK:
        _ACTIVE_JOBS.discard(doc_id)


def is_job_active(doc_id: str) -> bool:
    with _ACTIVE_LOCK:
        return doc_id in _ACTIVE_JOBS


def recover_stale_documents(db: Session, force_all: bool = False) -> int:
    """Detects documents stuck in non-terminal states ('uploading', 'processing', 'embedding', 'indexed')
    whose background workers are no longer active, and marks them as 'failed'.
    """
    stale_statuses = ["uploading", "processing", "embedding", "indexed"]
    stale_docs = db.scalars(
        select(Document).where(Document.status.in_(stale_statuses))
    ).all()
    recovered = 0
    for doc in stale_docs:
        if force_all or not is_job_active(doc.id):
            doc.status = "failed"
            doc.error_message = "Indexing interrupted by server restart/OOM. Please retry indexing."
            recovered += 1
    if recovered > 0:
        db.commit()
        logger.warning("recovered_stale_documents count=%d", recovered)
    return recovered


def process_document(document_id: str, session_factory: sessionmaker) -> None:
    """Runs in a background task. Never raises: failures are stored on the document."""
    mark_job_started(document_id)
    try:
        _execute_document_processing(document_id, session_factory)
    finally:
        mark_job_finished(document_id)


def _execute_document_processing(document_id: str, session_factory: sessionmaker) -> None:
    settings = get_settings()
    started = time.perf_counter()
    stage = "processing"
    with session_factory() as db:
        doc = db.get(Document, document_id)
        if doc is None:  # deleted before processing began
            return
        doc.status = stage
        doc.error_message = None
        db.commit()

        # 1. Text extraction
        try:
            path = Path(settings.upload_dir) / doc.stored_filename
            extraction = DocumentProcessor().extract(path)
        except PDFExtractionError as exc:
            db.rollback()
            _mark_failed(db, document_id, str(exc))
            return
        except Exception as exc:
            logger.exception("extraction_failed id=%s", document_id)
            db.rollback()
            _mark_failed(db, document_id, f"Extraction failed: {exc}")
            return

        # 2. Chunking
        stage = "chunking"
        try:
            chunks = Chunker(settings.chunk_size, settings.chunk_overlap).chunk_pages(
                extraction.pages, doc.id, doc.name
            )
            db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
            db.add_all(
                DocumentChunk(
                    id=c.chunk_id, document_id=c.document_id, chunk_index=c.chunk_index,
                    page_number=c.page_number, section=c.section, text=c.text,
                )
                for c in chunks
            )
            doc.page_count = extraction.page_count
            doc.chunk_count = len(chunks)
            doc.error_message = None
            stage = doc.status = "embedding"
            db.commit()
        except Exception as exc:
            logger.exception("chunking_failed id=%s", document_id)
            db.rollback()
            _mark_failed(db, document_id, f"Chunking failed: {exc}")
            return

        # 3. Embedding and Vector Indexing
        try:
            t_embed = time.perf_counter()
            embedder, store = deps.get_embedding_service(), deps.get_vector_store()
            vectors = embedder.embed_texts([c.text for c in chunks])  # one batched call
            store.delete_document(doc.id)  # makes reprocessing idempotent
            store.add(chunks, vectors)
            embed_seconds = time.perf_counter() - t_embed

            doc.status = "ready"
            doc.embedding_model = settings.embedding_model
            doc.error_message = None
            db.commit()
            deps.get_bm25_retriever().invalidate()  # BM25 index now includes this document
            logger.info(
                "document_processed id=%s pages=%d chunks=%d embed_seconds=%.2f total_seconds=%.2f",
                doc.id, extraction.page_count, len(chunks), embed_seconds, time.perf_counter() - started,
            )
        except MemoryError:
            logger.exception("embedding_oom id=%s", document_id)
            db.rollback()
            _mark_failed(
                db, document_id,
                "Out of memory during embedding. Please use remote API embeddings or a smaller document.",
            )
        except Exception as exc:
            logger.exception("embedding_failed id=%s err=%s", document_id, exc)
            db.rollback()
            _mark_failed(db, document_id, f"Embedding failed: {exc}")


def _mark_failed(db: Session, document_id: str, message: str) -> None:
    doc = db.get(Document, document_id)
    if doc:
        doc.status = "failed"
        doc.error_message = message
        db.commit()
    logger.warning("document_failed id=%s reason=%s", document_id, message)
