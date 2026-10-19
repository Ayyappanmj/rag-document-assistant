"""Cross-Encoder re-ranking for retrieved candidate passages."""
import logging
import time
from typing import Any, Protocol

from app.rag.hybrid_retriever import HybridResult

logger = logging.getLogger(__name__)


class CrossEncoderModel(Protocol):
    def predict(self, sentences: list[list[str] | tuple[str, str]]) -> Any: ...


class ReRanker:
    """Re-ranks retrieved candidates using a Cross-Encoder model.

    Cross-encoders process query and passage jointly through transformer cross-attention,
    yielding significantly higher retrieval precision than bi-encoder embeddings alone.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        enabled: bool = True,
        model: CrossEncoderModel | None = None,
    ):
        self.model_name = model_name
        self.enabled = enabled
        self._model = model

    def _get_model(self) -> CrossEncoderModel | None:
        if self._model is None and self.enabled:
            try:
                from sentence_transformers import CrossEncoder

                logger.info("loading_reranker_model name=%s", self.model_name)
                self._model = CrossEncoder(self.model_name)
            except Exception as exc:
                logger.error("failed_loading_reranker err=%s", exc)
                return None
        return self._model

    def rerank(
        self,
        query: str,
        candidates: list[HybridResult],
        top_k: int = 5,
    ) -> list[HybridResult]:
        if not self.enabled or not candidates or top_k <= 0:
            return candidates[:top_k]

        model = self._get_model()
        if model is None:
            return candidates[:top_k]

        started = time.perf_counter()
        pairs = [(query, c.text) for c in candidates]
        try:
            scores = model.predict(pairs)
        except Exception as exc:
            logger.error("rerank_inference_failed err=%s", exc)
            return candidates[:top_k]

        # Attach rerank score and update candidate ranking
        for candidate, raw_score in zip(candidates, scores):
            score_float = float(raw_score)
            candidate.rerank_score = score_float
            candidate.score = score_float

        reranked = sorted(
            candidates,
            key=lambda c: (c.rerank_score if c.rerank_score is not None else float("-inf")),
            reverse=True,
        )
        selected = reranked[:top_k]
        logger.info(
            "rerank_completed candidates=%d returned=%d latency_ms=%.1f",
            len(candidates),
            len(selected),
            (time.perf_counter() - started) * 1000,
        )
        return selected
