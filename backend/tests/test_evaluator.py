import pytest

from app.rag.evaluator import GroundingEvaluator, extract_claims, extract_numbers
from tests.fakes import FakeEmbeddingService

CONTEXT = [
    "Revenue increased by 18 percent in fiscal year 2025. "
    "The board approved a dividend of 2.5 dollars per share. "
    "Total headcount reached 1,842 employees."
]


@pytest.fixture
def evaluator():
    return GroundingEvaluator(FakeEmbeddingService())


def test_supported_answer_is_grounded(evaluator):
    r = evaluator.evaluate("Revenue increased by 18 percent in fiscal year 2025. [Source: a.pdf, Page 2]", CONTEXT)
    assert r.grounded is True
    assert r.faithfulness == 1.0 and r.confidence > 0.9
    assert r.unsupported_claims == []


def test_invented_fact_is_flagged(evaluator):
    r = evaluator.evaluate("The company opened a new office in Tokyo with many local staff members.", CONTEXT)
    assert r.grounded is False
    assert r.faithfulness == 0.0
    assert len(r.unsupported_claims) == 1


def test_wrong_number_fails_even_when_wording_matches(evaluator):
    r = evaluator.evaluate("Revenue increased by 25 percent in fiscal year 2025.", CONTEXT)
    assert r.grounded is False
    assert r.unsupported_numbers == ["25"]


def test_number_formats_are_normalised(evaluator):
    r = evaluator.evaluate("Total headcount reached 1842 employees.", CONTEXT)
    assert r.unsupported_numbers == [] and r.grounded is True


def test_partial_support_lowers_faithfulness(evaluator):
    answer = ("Revenue increased by 18 percent in fiscal year 2025. "
              "The company opened a new office in Tokyo with many local staff members.")
    r = evaluator.evaluate(answer, CONTEXT)
    assert r.faithfulness == 0.5
    assert r.grounded is False  # below the 0.8 minimum
    assert len(r.unsupported_claims) == 1


def test_min_faithfulness_is_configurable():
    lenient = GroundingEvaluator(FakeEmbeddingService(), min_faithfulness=0.5)
    answer = ("Revenue increased by 18 percent in fiscal year 2025. "
              "The company opened a new office in Tokyo with many local staff members.")
    assert lenient.evaluate(answer, CONTEXT).grounded is True


def test_nothing_checkable_returns_none(evaluator):
    r = evaluator.evaluate("According to the documents:\nYes.", CONTEXT)
    assert r.grounded is None and r.claims_checked == 0


def test_citation_markers_are_not_treated_as_claims(evaluator):
    claims = extract_claims("Revenue rose by ten percent this year. [Source: Annual_Report.pdf, Page 4]")
    assert claims == ["Revenue rose by ten percent this year."]


def test_extract_claims_handles_bullets_and_skips_questions_and_headings():
    answer = "Key points:\n- Revenue rose by ten percent\n- Costs fell by two percent\nWhy does this matter?"
    assert extract_claims(answer) == ["Revenue rose by ten percent", "Costs fell by two percent"]


def test_extract_numbers():
    assert extract_numbers("3 items, 18%, 1,842, 2.5, FY2025") == ["18", "1842", "2.5", "2025"]


def test_answer_relevance_higher_for_on_topic_answer(evaluator):
    q = "How many vacation days do employees get?"
    on = evaluator.answer_relevance(q, "Employees get twenty vacation days. [Source 1]")
    off = evaluator.answer_relevance(q, "The headquarters building has seven floors.")
    assert on > 0.4 > off
