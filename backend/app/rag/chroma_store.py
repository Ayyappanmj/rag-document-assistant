"""Chroma vector store (second backend next to FAISS). Free, open source, runs inside this process.

Differences from the FAISS store, on purpose:
  * Chroma is a database: it persists to disk by itself and keeps text + metadata next to the vectors.
  * Search is approximate (HNSW graph) instead of exact, and metadata filters run inside the database.
We hand Chroma our own embeddings, so its built-in embedding model is never used or downloaded.
"""
import logging
import threading
from pathlib import Path

import chromadb
import numpy as np
from chromadb.config import Settings as ChromaSettings

from app.rag.chunker import Chunk
from app.rag.vector_types import SearchResult

logger = logging.getLogger(__name__)

COLLECTION = "chunks"
WRITE_BATCH = 1000  # Chroma limits how many records one call may carry


def _open_collection(client):
    """Cosine space, so scores are comparable with the FAISS store. Newer Chroma uses `configuration`,
    older releases use the `hnsw:space` metadata key, so try both."""
    try:
        return client.get_or_create_collection(
            name=COLLECTION, configuration={"hnsw": {"space": "cosine"}}, embedding_function=None
        )
    except (TypeError, ValueError):
        return client.get_or_create_collection(
            name=COLLECTION, metadata={"hnsw:space": "cosine"}, embedding_function=None
        )


class ChromaVectorStore:
    name = "chroma"
    index_type = "HNSW (approximate search)"

    def __init__(self, persist_dir: str | Path):
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(persist_dir), settings=ChromaSettings(anonymized_telemetry=False)
        )
        self._collection = _open_collection(self._client)
        self._lock = threading.RLock()
        logger.info("chroma_store_opened vectors=%d", self.count)

    @property
    def count(self) -> int:
        with self._lock:
            return int(self._collection.count())

    def add(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        if not chunks:
            return
        vectors = np.ascontiguousarray(embeddings, dtype="float32")
        with self._lock:
            try:
                for start in range(0, len(chunks), WRITE_BATCH):
                    part = chunks[start:start + WRITE_BATCH]
                    self._collection.upsert(  # upsert = adding the same chunk id twice is harmless
                        ids=[c.chunk_id for c in part],
                        embeddings=vectors[start:start + WRITE_BATCH].tolist(),
                        documents=[c.text for c in part],
                        metadatas=[
                            {
                                "document_id": c.document_id,
                                "document_name": c.document_name,
                                "page_number": int(c.page_number),
                                "section": c.section or "",  # Chroma metadata cannot hold None
                            }
                            for c in part
                        ],
                    )
            except Exception as exc:
                if "dimension" in str(exc).lower():
                    raise ValueError("Embedding dimension does not match the existing index") from exc
                raise

    def search(
        self, query_vec: np.ndarray, top_k: int = 5, document_ids: list[str] | None = None
    ) -> list[SearchResult]:
        with self._lock:
            total = self._collection.count()
            if total == 0:
                return []
            where, available = None, total
            if document_ids:
                ids = list(document_ids)
                where = {"document_id": ids[0]} if len(ids) == 1 else {"document_id": {"$in": ids}}
                available = len(self._collection.get(where=where, include=[])["ids"])
                if available == 0:
                    return []
            query = np.ascontiguousarray(query_vec, dtype="float32").reshape(-1).tolist()
            res = self._collection.query(
                query_embeddings=[query], n_results=min(top_k, available), where=where,
                include=["documents", "metadatas", "distances"],
            )
        results: list[SearchResult] = []
        for chunk_id, text, meta, distance in zip(
            res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]
        ):
            results.append(SearchResult(
                chunk_id=chunk_id, document_id=meta["document_id"], document_name=meta["document_name"],
                page_number=int(meta["page_number"]), section=meta.get("section") or None, text=text,
                score=float(1.0 - distance),  # Chroma returns cosine distance, we expose similarity
            ))
        return results

    def delete_document(self, document_id: str) -> int:
        with self._lock:
            ids = self._collection.get(where={"document_id": document_id}, include=[])["ids"]
            for start in range(0, len(ids), WRITE_BATCH):
                self._collection.delete(ids=ids[start:start + WRITE_BATCH])
            return len(ids)
