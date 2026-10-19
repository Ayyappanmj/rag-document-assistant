"""Lightweight stand-in for the embedding model: hashed bag-of-words, normalised.
Texts sharing words get similar vectors, so retrieval tests are meaningful and fast."""
import re
import zlib

import numpy as np

DIM = 256


class FakeEmbeddingService:
    dimension = DIM

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(DIM, dtype="float32")
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            v[zlib.crc32(word.encode()) % DIM] += 1
        norm = np.linalg.norm(v)
        return v / norm if norm else v

    def embed_texts(self, texts):
        if not texts:
            return np.empty((0, DIM), dtype="float32")
        return np.stack([self._vec(t) for t in texts])

    def embed_query(self, query):
        return self._vec(query)
