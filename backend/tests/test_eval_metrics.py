import pytest

from app.rag.eval_metrics import answer_match, retrieval_precision_recall, summarize


def test_precision_recall_basic():
    assert retrieval_precision_recall(["a.pdf", "a.pdf", "b.pdf", "c.pdf"], ["a.pdf", "b.pdf"]) == (0.75, 1.0)


def test_precision_recall_missing_expected_document():
    assert retrieval_precision_recall(["a.pdf", "a.pdf"], ["a.pdf", "b.pdf"]) == (1.0, 0.5)


def test_precision_recall_nothing_retrieved_or_expected():
    assert retrieval_precision_recall([], ["a.pdf"]) == (0.0, 0.0)
    assert retrieval_precision_recall(["a.pdf"], []) == (None, None)


def test_answer_match_scores_overlap():
    assert answer_match("Revenue was USD 84.6 million.", "Revenue was USD 84.6 million [Source: a.pdf, Page 2]") == 1.0
    assert 0 < answer_match("Revenue was USD 84.6 million.", "Revenue was high.") < 1


def test_answer_match_number_formats_and_citations_ignored():
    assert answer_match("1,842 employees.", "The company had 1842 employees. [Source: a.pdf, Page 1]") == 1.0
    assert answer_match("Pune.", "[Source: Pune_Report.pdf, Page 1]") == 0.0  # marker text does not count


def test_answer_match_empty_expected():
    assert answer_match("", "anything") is None


def _row(**kw):
    base = dict(
        type="factual", answerable=True, faithfulness=1.0, answer_relevance=0.8, context_relevance=0.6,
        citation_coverage=1.0, retrieval_precision=1.0, retrieval_recall=1.0, top_retrieval_score=0.7,
        answer_match=0.9, latency_ms=1000.0, grounded=True, refused=False,
    )
    base.update(kw)
    return base


def test_summarize():
    rows = [
        _row(),
        _row(type="numerical", faithfulness=0.5, grounded=False, answer_match=0.5, latency_ms=3000.0),
        _row(type="unanswerable", answerable=False, faithfulness=None, answer_relevance=None,
             context_relevance=None, citation_coverage=None, retrieval_precision=None, retrieval_recall=None,
             answer_match=None, grounded=None, refused=True, latency_ms=100.0),
    ]
    s = summarize(rows)
    assert s["total_questions"] == 3 and s["answerable_questions"] == 2 and s["unanswerable_questions"] == 1
    assert s["faithfulness"] == 0.75
    assert s["answer_match"] == 0.7  # only answerable rows
    assert s["grounded_answers"] == 1 and s["potentially_hallucinated_answers"] == 1
    assert s["refusal_accuracy"] == 1.0 and s["false_refusal_rate"] == 0.0
    assert s["by_type"]["numerical"]["count"] == 1
    assert s["avg_latency_ms"] == pytest.approx(1366.667, abs=0.01)
