"""BM25 keyword retrieval (rank-bm25). The index is rebuilt lazily from the database
whenever documents change, so SQLite stays the single source of truth."""
import logging
import threading

import numpy as np
from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.models.database import Document, DocumentChunk
from app.rag.tokenizer import tokenize
from app.rag.vector_store import SearchResult

logger = logging.getLogger(__name__)

class BM25Retriever:
    def __init__(self, session_factory: sessionmaker):
        self._session_factory = session_factory
        self._lock = threading.RLock()
        self._dirty = True
        self._bm25: BM25Okapi | None = None
        self._entries: list[dict] = []

    def invalidate(self) -> None:
        """Call after documents are added or removed; the index rebuilds on the next search."""
        with self._lock:
            self._dirty = True

    @property
    def count(self) -> int:
        with self._lock:
            self._ensure_built()
            return len(self._entries)

    def _ensure_built(self) -> None:
        if not self._dirty:
            return
        with self._session_factory() as db:
            rows = db.execute(
                select(
                    DocumentChunk.id, DocumentChunk.document_id, Document.name,
                    DocumentChunk.page_number, DocumentChunk.section, DocumentChunk.text,
                )
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(Document.status == "ready")  # skip documents still processing or failed
                .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
            ).all()
        self._entries = [
            {"chunk_id": r[0], "document_id": r[1], "document_name": r[2],
             "page_number": r[3], "section": r[4], "text": r[5]}
            for r in rows
        ]
        corpus = [tokenize(e["text"]) for e in self._entries]
        self._bm25 = BM25Okapi(corpus) if any(corpus) else None
        if self._bm25 is not None:
            # Ensure non-negative IDF so matched query terms produce positive scores
            for word, idf in list(self._bm25.idf.items()):
                if idf <= 0:
                    self._bm25.idf[word] = 0.1
        self._dirty = False
        logger.info("bm25_index_built chunks=%d", len(self._entries))

    def search(
        self, query: str, top_k: int = 5, document_ids: list[str] | None = None
    ) -> list[SearchResult]:
        """Returns results with raw BM25 scores (unbounded; Phase 6 normalises them)."""
        tokens = tokenize(query)
        if not tokens:
            return []
        with self._lock:
            self._ensure_built()
            if self._bm25 is None:
                return []
            scores = np.asarray(self._bm25.get_scores(tokens), dtype=float)
            if document_ids:
                allowed = set(document_ids)
                mask = np.array([e["document_id"] in allowed for e in self._entries])
                scores = np.where(mask, scores, 0.0)
            order = np.argsort(-scores)[:top_k]
            return [
                SearchResult(score=float(scores[i]), **self._entries[i])
                for i in order if scores[i] > 0  # zero score = no query term matched
            ]
