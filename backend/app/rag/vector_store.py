"""FAISS vector store with JSON metadata sidecar and disk persistence."""
import json
import logging
import threading
from pathlib import Path

import faiss
import numpy as np

from app.rag.chunker import Chunk
from app.rag.vector_types import SearchResult  # re-exported: other modules import it from here

logger = logging.getLogger(__name__)

INDEX_FILE = "faiss.index"
META_FILE = "metadata.json"


class VectorStore:
    """Exact (flat) inner-product index. IDMap lets us delete one document's vectors."""

    name = "faiss"
    index_type = "Flat (exact search)"

    def __init__(self, index_dir: str | Path):
        self._dir = Path(index_dir)
        self._lock = threading.RLock()
        self._index: faiss.Index | None = None
        self._meta: dict[int, dict] = {}
        self._next_id = 0
        self.load()

    # ---- persistence -------------------------------------------------
    def load(self) -> None:
        index_path, meta_path = self._dir / INDEX_FILE, self._dir / META_FILE
        if not (index_path.exists() and meta_path.exists()):
            return
        with self._lock:
            self._index = faiss.read_index(str(index_path))
            data = json.loads(meta_path.read_text(encoding="utf-8"))
            self._next_id = data["next_id"]
            self._meta = {int(k): v for k, v in data["items"].items()}
        logger.info("vector_index_loaded vectors=%d", self.count)

    def save(self) -> None:
        with self._lock:
            if self._index is None:
                return
            self._dir.mkdir(parents=True, exist_ok=True)
            tmp_index, tmp_meta = self._dir / "faiss.tmp", self._dir / "meta.tmp"
            faiss.write_index(self._index, str(tmp_index))
            tmp_meta.write_text(
                json.dumps({"next_id": self._next_id, "items": self._meta}), encoding="utf-8"
            )
            tmp_index.replace(self._dir / INDEX_FILE)  # replace after writing = no half-written index
            tmp_meta.replace(self._dir / META_FILE)

    # ---- operations --------------------------------------------------
    @property
    def count(self) -> int:
        return int(self._index.ntotal) if self._index is not None else 0

    def add(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")
        if not chunks:
            return
        vecs = np.ascontiguousarray(embeddings, dtype="float32")
        with self._lock:
            if self._index is None:
                self._index = faiss.IndexIDMap2(faiss.IndexFlatIP(vecs.shape[1]))
            elif vecs.shape[1] != self._index.d:
                raise ValueError("Embedding dimension does not match the existing index")
            ids = np.arange(self._next_id, self._next_id + len(chunks), dtype="int64")
            self._index.add_with_ids(vecs, ids)
            for faiss_id, c in zip(ids, chunks):
                self._meta[int(faiss_id)] = {
                    "chunk_id": c.chunk_id, "document_id": c.document_id,
                    "document_name": c.document_name, "page_number": c.page_number,
                    "section": c.section, "text": c.text,
                }
            self._next_id += len(chunks)
            self.save()

    def search(
        self, query_vec: np.ndarray, top_k: int = 5, document_ids: list[str] | None = None
    ) -> list[SearchResult]:
        with self._lock:
            if self._index is None or self._index.ntotal == 0:
                return []
            q = np.ascontiguousarray(query_vec.reshape(1, -1), dtype="float32")
            # With a document filter, scan everything then filter (flat index is brute force anyway).
            k = self._index.ntotal if document_ids else min(top_k, self._index.ntotal)
            scores, ids = self._index.search(q, k)
            allowed = set(document_ids) if document_ids else None
            results: list[SearchResult] = []
            for score, faiss_id in zip(scores[0], ids[0]):
                meta = self._meta.get(int(faiss_id))
                if faiss_id == -1 or meta is None:
                    continue
                if allowed is not None and meta["document_id"] not in allowed:
                    continue
                results.append(SearchResult(score=float(score), **meta))
                if len(results) == top_k:
                    break
            return results

    def delete_document(self, document_id: str) -> int:
        """Remove all vectors for a document. Returns how many were removed."""
        with self._lock:
            if self._index is None:
                return 0
            ids = [i for i, m in self._meta.items() if m["document_id"] == document_id]
            if not ids:
                return 0
            self._index.remove_ids(np.array(ids, dtype="int64"))
            for i in ids:
                del self._meta[i]
            self.save()
            return len(ids)
