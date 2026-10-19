import numpy as np
import pytest

from app.rag.hybrid_retriever import HybridRetriever, min_max_normalize, preprocess_query
from app.rag.vector_store import SearchResult


def sr(chunk_id, score, doc="d1"):
    return SearchResult(chunk_id, doc, f"{doc}.pdf", 1, None, f"text of {chunk_id}", score)


class StubStore:
    def __init__(self, results):
        self.results, self.calls = results, []

    def search(self, vec, top_k, document_ids):
        self.calls.append((top_k, document_ids))
        return self.results[:top_k]


class StubEmbedder:
    def embed_query(self, q):
        return np.zeros(4, dtype="float32")


class StubBM25:
    def __init__(self, results):
        self.results, self.calls = results, []

    def search(self, query, top_k, document_ids):
        self.calls.append((top_k, document_ids))
        return self.results[:top_k]


def make(dense, bm25, **kw):
    return HybridRetriever(StubEmbedder(), StubStore(dense), StubBM25(bm25), **kw)


DENSE = [sr("A", 0.9), sr("B", 0.5), sr("C", 0.1)]
BM25 = [sr("B", 10.0), sr("D", 5.0)]


def test_min_max_normalize():
    assert min_max_normalize({"a": 1.0, "b": 3.0, "c": 2.0}) == {"a": 0.0, "b": 1.0, "c": 0.5}
    assert min_max_normalize({}) == {}


def test_min_max_degenerate_cases():
    assert min_max_normalize({"a": 2.0}) == {"a": 1.0}
    assert min_max_normalize({"a": 0.0, "b": 0.0}) == {"a": 0.0, "b": 0.0}


def test_preprocess_query():
    assert preprocess_query("  What   was\n revenue?  ") == "What was revenue?"
    assert len(preprocess_query("x" * 5000)) == 1000


def test_weighted_fusion_scores_and_order():
    results = make(DENSE, BM25, dense_weight=0.7, bm25_weight=0.3).retrieve("q", top_k=2)
    assert [r.chunk_id for r in results] == ["A", "B"]
    assert results[0].score == pytest.approx(0.7)          # A: 0.7*1 + 0.3*0
    assert results[1].score == pytest.approx(0.65)         # B: 0.7*0.5 + 0.3*1


def test_weights_change_ranking():
    results = make(DENSE, BM25, dense_weight=0.2, bm25_weight=0.8).retrieve("q", top_k=2)
    assert results[0].chunk_id == "B"


def test_unnormalised_weights_are_rescaled():
    a = make(DENSE, BM25, dense_weight=7, bm25_weight=3).retrieve("q", top_k=3)
    b = make(DENSE, BM25, dense_weight=0.7, bm25_weight=0.3).retrieve("q", top_k=3)
    assert [(r.chunk_id, round(r.score, 6)) for r in a] == [(r.chunk_id, round(r.score, 6)) for r in b]


def test_chunk_in_both_lists_appears_once_with_both_raw_scores():
    results = make(DENSE, BM25).retrieve("q", top_k=10)
    ids = [r.chunk_id for r in results]
    assert len(ids) == len(set(ids)) == 4  # A, B, C, D
    b = next(r for r in results if r.chunk_id == "B")
    assert b.dense_score == 0.5 and b.bm25_score == 10.0
    a = next(r for r in results if r.chunk_id == "A")
    assert a.bm25_score is None


def test_top_k_respected_and_empty_inputs():
    assert len(make(DENSE, BM25).retrieve("q", top_k=1)) == 1
    assert make([], []).retrieve("q") == []
    assert make(DENSE, BM25).retrieve("   ") == []


def test_works_when_only_one_retriever_returns_results():
    results = make([], BM25).retrieve("q", top_k=5)
    assert results[0].chunk_id == "B" and results[0].dense_score is None


def test_candidate_pool_and_filter_forwarded():
    hr = make(DENSE, BM25, candidate_pool=20)
    hr.retrieve("q", top_k=5, document_ids=["d1"])
    assert hr._store.calls[0] == (20, ["d1"]) and hr._bm25.calls[0] == (20, ["d1"])


def test_invalid_weights_rejected():
    with pytest.raises(ValueError):
        make(DENSE, BM25, dense_weight=-1, bm25_weight=1)
    with pytest.raises(ValueError):
        make(DENSE, BM25, dense_weight=0, bm25_weight=0)
