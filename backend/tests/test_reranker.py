import numpy as np
import pytest

from app.rag.hybrid_retriever import HybridResult, HybridRetriever
from app.rag.reranker import ReRanker
from app.rag.vector_store import SearchResult


class StubCrossEncoder:
    def __init__(self, score_map: dict[str, float]):
        self.score_map = score_map

    def predict(self, pairs):
        # pairs is a list of (query, text)
        return [self.score_map.get(text, 0.0) for _, text in pairs]


def make_result(chunk_id: str, text: str, score: float = 0.5) -> HybridResult:
    return HybridResult(
        chunk_id=chunk_id,
        document_id="doc1",
        document_name="doc1.pdf",
        page_number=1,
        section=None,
        text=text,
        score=score,
        dense_score=score,
        bm25_score=score * 10,
    )


def test_reranker_reorders_candidates_by_cross_encoder_score():
    c1 = make_result("chunk-1", "Passage about cats", 0.9)
    c2 = make_result("chunk-2", "Passage specifically about quantum physics", 0.2)
    c3 = make_result("chunk-3", "General physics intro", 0.5)

    # CrossEncoder predicts c2 is the most relevant to quantum physics, then c3, then c1
    stub_model = StubCrossEncoder({
        "Passage specifically about quantum physics": 0.95,
        "General physics intro": 0.65,
        "Passage about cats": -0.8,
    })

    reranker = ReRanker(enabled=True, model=stub_model)
    results = reranker.rerank("What is quantum entanglement?", [c1, c2, c3], top_k=2)

    assert len(results) == 2
    assert results[0].chunk_id == "chunk-2"
    assert results[0].rerank_score == pytest.approx(0.95)
    assert results[1].chunk_id == "chunk-3"
    assert results[1].rerank_score == pytest.approx(0.65)


def test_reranker_disabled_preserves_original_order():
    c1 = make_result("chunk-1", "Text 1", 0.9)
    c2 = make_result("chunk-2", "Text 2", 0.8)

    stub_model = StubCrossEncoder({"Text 1": 0.1, "Text 2": 0.99})
    reranker = ReRanker(enabled=False, model=stub_model)

    results = reranker.rerank("query", [c1, c2], top_k=2)
    assert [r.chunk_id for r in results] == ["chunk-1", "chunk-2"]


def test_reranker_empty_and_zero_top_k():
    reranker = ReRanker(enabled=True)
    assert reranker.rerank("query", [], top_k=5) == []

    c1 = make_result("chunk-1", "Text 1", 0.9)
    assert reranker.rerank("query", [c1], top_k=0) == []
