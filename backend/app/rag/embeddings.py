"""Embedding service: wraps Sentence Transformers with lazy loading, batching and a query cache."""
import logging
import threading
from collections import OrderedDict

import numpy as np

logger = logging.getLogger(__name__)

QUERY_CACHE_SIZE = 256


class EmbeddingService:
    """Produces L2-normalised vectors, so inner product == cosine similarity."""

    def __init__(self, model_name: str, batch_size: int = 32):
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None
        self._lock = threading.Lock()
        self._query_cache: OrderedDict[str, np.ndarray] = OrderedDict()

    def _load(self):
        with self._lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer  # heavy import, keep lazy

                logger.info("embedding_model_loading model=%s", self.model_name)
                self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        return int(self._load().get_sentence_embedding_dimension())

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Batch-embed many texts. Returns float32 array of shape (n, dim)."""
        if not texts:
            return np.empty((0, 0), dtype="float32")
        vectors = self._load().encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype="float32")

    def embed_query(self, query: str) -> np.ndarray:
        """Embed one query, caching recent ones so repeated questions are free."""
        key = query.strip()
        if key in self._query_cache:
            self._query_cache.move_to_end(key)
            return self._query_cache[key]
        vec = self.embed_texts([key])[0]
        self._query_cache[key] = vec
        if len(self._query_cache) > QUERY_CACHE_SIZE:
            self._query_cache.popitem(last=False)
        return vec
