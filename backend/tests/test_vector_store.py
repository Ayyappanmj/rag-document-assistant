import numpy as np
import pytest

from app.rag.chunker import Chunk
from app.rag.vector_store import VectorStore
from tests.fakes import FakeEmbeddingService

emb = FakeEmbeddingService()


def _chunks():
    data = [
        ("d1", "a.pdf", 1, "Revenue grew eighteen percent in fiscal 2025."),
        ("d1", "a.pdf", 2, "The board approved a new dividend policy."),
        ("d2", "b.pdf", 7, "Employees receive twenty vacation days per year."),
    ]
    return [Chunk(f"{d}_{i}", d, n, p, i, t) for i, (d, n, p, t) in enumerate(data)]


def _store(tmp_path):
    store = VectorStore(tmp_path)
    chunks = _chunks()
    store.add(chunks, emb.embed_texts([c.text for c in chunks]))
    return store


def test_empty_store_returns_nothing(tmp_path):
    assert VectorStore(tmp_path).search(emb.embed_query("anything")) == []


def test_search_ranks_relevant_chunk_first(tmp_path):
    hits = _store(tmp_path).search(emb.embed_query("vacation days for employees"), top_k=2)
    assert hits[0].document_name == "b.pdf" and hits[0].page_number == 7
    assert hits[0].score >= hits[1].score


def test_persistence_round_trip(tmp_path):
    _store(tmp_path)
    reloaded = VectorStore(tmp_path)  # new instance reads files from disk
    assert reloaded.count == 3
    hit = reloaded.search(emb.embed_query("dividend policy"), top_k=1)[0]
    assert hit.page_number == 2


def test_document_filter(tmp_path):
    hits = _store(tmp_path).search(emb.embed_query("revenue"), top_k=5, document_ids=["d2"])
    assert hits and all(h.document_id == "d2" for h in hits)


def test_delete_document(tmp_path):
    store = _store(tmp_path)
    assert store.delete_document("d1") == 2
    assert store.count == 1
    assert all(h.document_id == "d2" for h in store.search(emb.embed_query("revenue"), top_k=5))
    assert VectorStore(tmp_path).count == 1  # deletion persisted


def test_dimension_mismatch_rejected(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError):
        store.add(_chunks()[:1], np.ones((1, 8), dtype="float32"))


def test_length_mismatch_rejected(tmp_path):
    with pytest.raises(ValueError):
        VectorStore(tmp_path).add(_chunks(), np.ones((1, 4), dtype="float32"))
