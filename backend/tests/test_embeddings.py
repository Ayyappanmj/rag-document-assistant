import os

import numpy as np
import pytest

from app.rag.embeddings import EmbeddingService


class StubModel:
    """Mimics SentenceTransformer so we can test our wrapper without downloading anything."""
    def __init__(self):
        self.encode_calls = 0

    def get_sentence_embedding_dimension(self):
        return 4

    def encode(self, texts, **kwargs):
        self.encode_calls += 1
        assert kwargs["normalize_embeddings"] is True
        return np.ones((len(texts), 4), dtype="float64")


def _service():
    svc = EmbeddingService("stub", batch_size=8)
    svc._model = StubModel()
    return svc


def test_embed_texts_shape_and_dtype():
    out = _service().embed_texts(["a", "b", "c"])
    assert out.shape == (3, 4) and out.dtype == np.float32


def test_embed_empty_list():
    assert len(_service().embed_texts([])) == 0


def test_query_embeddings_are_cached():
    svc = _service()
    svc.embed_query("what is revenue?")
    svc.embed_query("what is revenue?")
    assert svc._model.encode_calls == 1


@pytest.mark.skipif(not os.getenv("RUN_SLOW_TESTS"), reason="downloads the real model; set RUN_SLOW_TESTS=1")
def test_real_model_dimension_and_normalisation():
    svc = EmbeddingService("sentence-transformers/all-MiniLM-L6-v2")
    assert svc.dimension == 384
    vec = svc.embed_query("hello world")
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-3


def test_texts_are_encoded_in_one_batched_call_with_configured_batch_size():
    seen = {}

    class Model(StubModel):
        def encode(self, texts, **kwargs):
            seen.update(count=len(texts), batch_size=kwargs["batch_size"])
            return super().encode(texts, **kwargs)

    svc = EmbeddingService("stub", batch_size=16)
    svc._model = Model()
    svc.embed_texts([f"chunk {i}" for i in range(100)])
    assert seen == {"count": 100, "batch_size": 16}
    assert svc._model.encode_calls == 1


def test_dimension_comes_from_the_model():
    assert _service().dimension == 4
