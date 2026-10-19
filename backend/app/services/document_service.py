"""Orchestrates document processing: extract -> chunk -> embed -> index."""
import logging
import time
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.models.database import Document, DocumentChunk
from app.rag import dependencies as deps
from app.rag.chunker import Chunker
from app.rag.document_processor import DocumentProcessor, PDFExtractionError

logger = logging.getLogger(__name__)


def process_document(document_id: str, session_factory: sessionmaker) -> None:
    """Runs in a background task. Never raises: failures are stored on the document."""
    settings = get_settings()
    started = time.perf_counter()
    stage = "processing"
    with session_factory() as db:
        doc = db.get(Document, document_id)
        if doc is None:  # deleted before processing began
            return
        try:
            doc.status = stage
            db.commit()

            path = Path(settings.upload_dir) / doc.stored_filename
            extraction = DocumentProcessor().extract(path)
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

            t_embed = time.perf_counter()
            embedder, store = deps.get_embedding_service(), deps.get_vector_store()
            vectors = embedder.embed_texts([c.text for c in chunks])  # one batched call
            store.delete_document(doc.id)  # makes reprocessing idempotent
            store.add(chunks, vectors)
            embed_seconds = time.perf_counter() - t_embed

            stage = doc.status = "indexed"
            db.commit()
            doc.status = "ready"
            doc.embedding_model = settings.embedding_model
            db.commit()
            deps.get_bm25_retriever().invalidate()  # BM25 index now includes this document
            logger.info(
                "document_processed id=%s pages=%d chunks=%d embed_seconds=%.2f total_seconds=%.2f",
                doc.id, extraction.page_count, len(chunks), embed_seconds, time.perf_counter() - started,
            )
        except PDFExtractionError as exc:
            db.rollback()
            _mark_failed(db, document_id, str(exc))
        except Exception:
            logger.exception("document_processing_failed id=%s stage=%s", document_id, stage)
            db.rollback()
            _mark_failed(db, document_id, f"Failed during {stage}. Check the server logs for details.")


def _mark_failed(db, document_id: str, message: str) -> None:
    doc = db.get(Document, document_id)
    if doc:
        doc.status = "failed"
        doc.error_message = message
        db.commit()
    logger.warning("document_failed id=%s reason=%s", document_id, message)
