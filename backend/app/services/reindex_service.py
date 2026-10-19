"""Rebuilds a vector index from the chunks stored in the database.

Use it after switching VECTOR_STORE (the new database starts empty), or to recover a lost index.
The chunk text is already in SQLite, so only the embeddings are recomputed."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.database import Document, DocumentChunk
from app.rag.chunker import Chunk
from app.rag.vector_types import VectorIndex

logger = logging.getLogger(__name__)


def reindex_documents(db: Session, embedder, store: VectorIndex) -> dict:
    documents = db.scalars(select(Document).where(Document.status == "ready").order_by(Document.created_at)).all()
    indexed_docs = indexed_chunks = 0
    for doc in documents:
        rows = db.scalars(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id).order_by(DocumentChunk.chunk_index)
        ).all()
        if not rows:
            continue
        chunks = [
            Chunk(r.id, doc.id, doc.name, r.page_number, r.chunk_index, r.text, r.section) for r in rows
        ]
        vectors = embedder.embed_texts([c.text for c in chunks])
        store.delete_document(doc.id)  # makes re-running safe
        store.add(chunks, vectors)
        indexed_docs += 1
        indexed_chunks += len(chunks)
        logger.info("reindexed document=%s chunks=%d store=%s", doc.id, len(chunks), store.name)
    return {"documents": indexed_docs, "chunks": indexed_chunks, "store": store.name}
