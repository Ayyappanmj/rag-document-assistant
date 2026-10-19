"""Hybrid retrieval: FAISS (semantic) + BM25 (keyword), min-max normalised and weight-fused."""
import logging
import re
import time
import unicodedata
from dataclasses import dataclass

from app.rag.vector_store import SearchResult

logger = logging.getLogger(__name__)

MAX_QUERY_CHARS = 1000


@dataclass
class HybridResult:
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section: str | None
    text: str
    score: float                    # fused score, 0..1, relative to this query's candidates
    dense_score: float | None       # raw cosine similarity (None if FAISS did not return it)
    bm25_score: float | None        # raw BM25 score (None if BM25 did not return it)
    rerank_score: float | None = None  # cross-encoder score if reranker was used


def preprocess_query(query: str) -> str:
    """Normalise unicode, collapse whitespace, cap length."""
    query = unicodedata.normalize("NFKC", query)
    return re.sub(r"\s+", " ", query).strip()[:MAX_QUERY_CHARS]


def min_max_normalize(scores: dict[str, float]) -> dict[str, float]:
    """Scale scores to 0..1. If all scores are equal, matches get 1.0 (or 0.0 if the score is not positive)."""
    if not scores:
        return {}
    lo, hi = min(scores.values()), max(scores.values())
    if hi - lo < 1e-12:
        return {k: 1.0 if hi > 0 else 0.0 for k in scores}
    return {k: (v - lo) / (hi - lo) for k, v in scores.items()}


class HybridRetriever:
    def __init__(
        self, embedder, vector_store, bm25, dense_weight: float = 0.7,
        bm25_weight: float = 0.3, candidate_pool: int = 20, reranker=None,
    ):
        if dense_weight < 0 or bm25_weight < 0 or dense_weight + bm25_weight <= 0:
            raise ValueError("Weights must be non-negative and not both zero")
        total = dense_weight + bm25_weight  # normalise so they always sum to 1
        self.dense_weight = dense_weight / total
        self.bm25_weight = bm25_weight / total
        self._embedder, self._store, self._bm25 = embedder, vector_store, bm25
        self._candidate_pool = candidate_pool
        self._reranker = reranker

    def retrieve(
        self, query: str, top_k: int = 5, document_ids: list[str] | None = None
    ) -> list[HybridResult]:
        query = preprocess_query(query)
        if not query:
            return []
        # Pull more candidates than top_k so fusion has something to re-rank.
        k = max(top_k * 4, self._candidate_pool)

        t0 = time.perf_counter()
        dense_hits = self._store.search(self._embedder.embed_query(query), k, document_ids)
        t1 = time.perf_counter()
        bm25_hits = self._bm25.search(query, k, document_ids)
        t2 = time.perf_counter()

        dense_raw = {h.chunk_id: h.score for h in dense_hits}
        bm25_raw = {h.chunk_id: h.score for h in bm25_hits}
        dense_norm, bm25_norm = min_max_normalize(dense_raw), min_max_normalize(bm25_raw)
        by_id = {h.chunk_id: h for h in [*bm25_hits, *dense_hits]}  # one record per chunk

        fused: list[HybridResult] = []
        for chunk_id, hit in by_id.items():
            score = (self.dense_weight * dense_norm.get(chunk_id, 0.0)
                     + self.bm25_weight * bm25_norm.get(chunk_id, 0.0))
            fused.append(HybridResult(
                chunk_id=chunk_id, document_id=hit.document_id, document_name=hit.document_name,
                page_number=hit.page_number, section=hit.section, text=hit.text, score=score,
                dense_score=dense_raw.get(chunk_id), bm25_score=bm25_raw.get(chunk_id),
            ))
        fused.sort(key=lambda r: (-r.score, -(r.dense_score or 0.0)))

        # If a reranker is configured, re-rank candidate pool
        if self._reranker is not None:
            candidates = fused[:self._candidate_pool]
            top = self._reranker.rerank(query, candidates, top_k=top_k)
        else:
            top = fused[:top_k]

        logger.info(
            "hybrid_retrieval candidates=%d returned=%d dense_ms=%.1f bm25_ms=%.1f fusion_ms=%.1f reranked=%s",
            len(fused), len(top), (t1 - t0) * 1000, (t2 - t1) * 1000, (time.perf_counter() - t2) * 1000,
            bool(self._reranker),
        )
        return top
