"""Pure functions for scoring an evaluation run. All scores are simple, transparent heuristics."""
import re
from statistics import mean

from app.rag.citation import strip_citations
from app.rag.tokenizer import tokenize


def retrieval_precision_recall(
    retrieved_docs: list[str], expected_docs: list[str]
) -> tuple[float | None, float | None]:
    """Document-level scores. Precision: share of retrieved chunks from an expected document.
    Recall: share of expected documents that appear in the retrieved chunks.
    Returns (None, None) when no document is expected (unanswerable questions)."""
    if not expected_docs:
        return None, None
    if not retrieved_docs:
        return 0.0, 0.0
    expected = set(expected_docs)
    precision = sum(d in expected for d in retrieved_docs) / len(retrieved_docs)
    recall = len(expected & set(retrieved_docs)) / len(expected)
    return round(precision, 3), round(recall, 3)


def _tokens(text: str) -> list[str]:
    return tokenize(re.sub(r"(?<=\d),(?=\d)", "", text))  # 1,842 == 1842


def answer_match(ground_truth: str, answer: str) -> float | None:
    """Share of the expected answer's content words and numbers that appear in the generated answer.
    A lexical proxy for correctness, not a human judgement."""
    expected = set(_tokens(ground_truth))
    if not expected:
        return None
    produced = set(_tokens(strip_citations(answer)))
    return round(len(expected & produced) / len(expected), 3)


def _avg(values: list[float | None]) -> float | None:
    kept = [v for v in values if v is not None]
    return round(mean(kept), 3) if kept else None


def summarize(rows: list[dict]) -> dict:
    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    by_type: dict[str, dict] = {}
    for t in sorted({r["type"] for r in rows}):
        group = [r for r in rows if r["type"] == t]
        by_type[t] = {
            "count": len(group),
            "answer_match": _avg([r["answer_match"] for r in group]),
            "faithfulness": _avg([r["faithfulness"] for r in group]),
            "avg_latency_ms": _avg([r["latency_ms"] for r in group]),
        }
    return {
        "total_questions": len(rows),
        "answerable_questions": len(answerable),
        "unanswerable_questions": len(unanswerable),
        "faithfulness": _avg([r["faithfulness"] for r in rows]),
        "answer_relevance": _avg([r["answer_relevance"] for r in rows]),
        "context_relevance": _avg([r["context_relevance"] for r in rows]),
        "citation_coverage": _avg([r["citation_coverage"] for r in rows]),
        "retrieval_precision": _avg([r["retrieval_precision"] for r in rows]),
        "retrieval_recall": _avg([r["retrieval_recall"] for r in rows]),
        "avg_retrieval_score": _avg([r["top_retrieval_score"] for r in rows]),
        "answer_match": _avg([r["answer_match"] for r in answerable]),
        "avg_latency_ms": _avg([r["latency_ms"] for r in rows]),
        "grounded_answers": sum(r["grounded"] is True for r in rows),
        "potentially_hallucinated_answers": sum(r["grounded"] is False for r in rows),
        "refusal_accuracy": _avg([1.0 if r["refused"] else 0.0 for r in unanswerable]),
        "false_refusal_rate": _avg([1.0 if r["refused"] else 0.0 for r in answerable]),
        "by_type": by_type,
    }
