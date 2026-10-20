"""Embedding service: wraps Sentence Transformers and remote API providers with caching and memory safety."""
import gc
import logging
import os
import threading
from collections import OrderedDict
from typing import Optional

import httpx
import numpy as np

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

logger = logging.getLogger(__name__)

QUERY_CACHE_SIZE = 256


class EmbeddingService:
    """Produces L2-normalised vectors, so inner product == cosine similarity.
    
    Supports:
    - 'local': SentenceTransformer with CPU, batching, and memory constraints.
    - 'openai': Remote OpenAI-compatible API (e.g. text-embedding-3-small).
    - 'ollama': Remote Ollama /api/embed API.
    """

    def __init__(
        self,
        model_name: str,
        batch_size: int = 8,
        provider: str = "local",
        api_key: str = "",
        base_url: str = "",
    ):
        self.provider = (provider or "local").lower().strip()
        self.batch_size = batch_size
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") if base_url else ""
        self._dimension: Optional[int] = None
        self._model = None
        self._lock = threading.Lock()
        self._query_cache: OrderedDict[str, np.ndarray] = OrderedDict()

        if self.provider == "openai":
            if "sentence-transformers" in model_name or not model_name:
                self.model_name = "text-embedding-3-small"
            else:
                self.model_name = model_name
            if not self.base_url:
                self.base_url = "https://api.openai.com/v1"
        elif self.provider == "ollama":
            if "sentence-transformers" in model_name or not model_name:
                self.model_name = "nomic-embed-text"
            else:
                self.model_name = model_name
            if not self.base_url:
                self.base_url = "http://localhost:11434"
        else:
            self.model_name = model_name

    def _load_local_model(self):
        with self._lock:
            if self._model is None:
                try:
                    import torch
                    torch.set_num_threads(1)
                    if hasattr(torch, "set_num_interop_threads"):
                        torch.set_num_interop_threads(1)
                except Exception:
                    pass

                from sentence_transformers import SentenceTransformer  # heavy import, keep lazy

                logger.info("embedding_model_loading model=%s", self.model_name)
                self._model = SentenceTransformer(self.model_name, device="cpu")
        return self._model

    @property
    def dimension(self) -> int:
        if self._dimension is not None:
            return self._dimension
        if self.provider == "local":
            model = self._model if self._model is not None else self._load_local_model()
            if hasattr(model, "get_sentence_embedding_dimension"):
                self._dimension = int(model.get_sentence_embedding_dimension())
                return self._dimension
        probe = self.embed_texts(["probe"])
        self._dimension = int(probe.shape[1])
        return self._dimension

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Batch-embed many texts. Returns float32 array of shape (n, dim)."""
        if not texts:
            return np.empty((0, 0), dtype="float32")
        if self.provider == "openai":
            return self._embed_openai(texts)
        elif self.provider == "ollama":
            return self._embed_ollama(texts)
        else:
            return self._embed_local(texts)

    def _embed_local(self, texts: list[str]) -> np.ndarray:
        import torch

        model = self._model if self._model is not None else self._load_local_model()
        with torch.inference_mode():
            vectors = model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        gc.collect()
        return np.asarray(vectors, dtype="float32")

    def _embed_openai(self, texts: list[str]) -> np.ndarray:
        all_vectors = []
        batch_size = max(self.batch_size, 32)
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        with httpx.Client(timeout=60.0) as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                resp = client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json={"model": self.model_name, "input": batch},
                )
                resp.raise_for_status()
                data = resp.json()
                sorted_items = sorted(data["data"], key=lambda x: x["index"])
                for item in sorted_items:
                    vec = np.asarray(item["embedding"], dtype="float32")
                    norm = np.linalg.norm(vec)
                    if norm > 0:
                        vec = vec / norm
                    all_vectors.append(vec)
        return np.vstack(all_vectors)

    def _embed_ollama(self, texts: list[str]) -> np.ndarray:
        all_vectors = []
        with httpx.Client(timeout=60.0) as client:
            try:
                resp = client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model_name, "input": texts},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for emb in data.get("embeddings", []):
                        vec = np.asarray(emb, dtype="float32")
                        norm = np.linalg.norm(vec)
                        if norm > 0:
                            vec = vec / norm
                        all_vectors.append(vec)
                    return np.vstack(all_vectors)
            except Exception:
                pass

            for t in texts:
                resp = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model_name, "prompt": t},
                )
                resp.raise_for_status()
                vec = np.asarray(resp.json()["embedding"], dtype="float32")
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                all_vectors.append(vec)
        return np.vstack(all_vectors)

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
