import pytest

from app.rag.citation import citation_coverage, process_citations
from app.rag.hybrid_retriever import HybridResult


def src(i, doc="Annual_Report.pdf", page=42):
    return HybridResult(f"c{i}", "d", doc, page, None, f"text {i}", 0.5, 0.5, None)


SOURCES = [src(1, "Annual_Report.pdf", 42), src(2, "Financial_Report.pdf", 18), src(3, "Annual_Report.pdf", 7)]


def test_marker_rewritten_to_readable_form():
    r = process_citations("Revenue rose 18 percent in 2025. [Source 1]", SOURCES)
    assert r.answer == "Revenue rose 18 percent in 2025. [Source: Annual_Report.pdf, Page 42]"
    assert [s.chunk_id for s in r.cited_sources] == ["c1"]


@pytest.mark.parametrize("text", [
    "Fact. [Source 1, 2]", "Fact. [Sources 1 and 2]", "Fact. [Source 1][Source 2]",
    "Fact. (Source 1) (Source 2)", "Fact. [source: 1; 2]", "Fact. [SOURCE 1 & 2]",
])
def test_marker_variants_all_detected(text):
    r = process_citations(text, SOURCES)
    assert [s.chunk_id for s in r.cited_sources] == ["c1", "c2"]
    assert "[Source: Financial_Report.pdf, Page 18]" in r.answer


def test_cited_sources_unique_and_in_order_of_first_use():
    r = process_citations("A is true here now. [Source 3] B is true here now. [Source 1] C too. [Source 3]", SOURCES)
    assert [s.chunk_id for s in r.cited_sources] == ["c3", "c1"]


def test_duplicate_labels_in_one_group_collapsed():
    sources = [src(1, "a.pdf", 5), src(2, "a.pdf", 5)]
    r = process_citations("Fact. [Source 1][Source 2]", sources)
    assert r.answer.count("[Source: a.pdf, Page 5]") == 1
    assert len(r.cited_sources) == 2


def test_invalid_numbers_removed_and_reported():
    r = process_citations("Revenue rose sharply this year. [Source 9]", SOURCES)
    assert r.invalid_numbers == [9]
    assert r.cited_sources == []
    assert r.answer == "Revenue rose sharply this year."
    assert r.coverage == 0.0


def test_mixed_valid_and_invalid_group_keeps_valid():
    r = process_citations("Revenue rose sharply this year. [Sources 1, 9]", SOURCES)
    assert r.invalid_numbers == [9]
    assert [s.chunk_id for s in r.cited_sources] == ["c1"]


def test_non_citations_left_alone():
    text = "In (2025) the firm grew [2] times, see Note 3."
    assert process_citations(text, SOURCES).answer == text


def test_no_markers():
    r = process_citations("Revenue rose sharply this year.", SOURCES)
    assert r.cited_sources == [] and r.coverage == 0.0


def test_coverage_counts_cited_sentences():
    answer = "Revenue rose 18 percent in 2025. [Source 1] Costs also fell by two percent."
    assert citation_coverage(answer, 3) == 0.5


def test_coverage_marker_after_full_stop_belongs_to_previous_sentence():
    assert citation_coverage("Revenue rose 18 percent in 2025. [Source 1]", 3) == 1.0


def test_coverage_ignores_headings_and_short_fragments():
    answer = "According to the documents:\nRevenue rose 18 percent in 2025 [Source 1].\nYes."
    assert citation_coverage(answer, 3) == 1.0


def test_coverage_bullets():
    answer = "- Revenue rose 18 percent [Source 1]\n- Costs fell two percent [Source 2]\n- Headcount grew by ten percent"
    assert citation_coverage(answer, 3) == pytest.approx(2 / 3)


def test_coverage_ignores_out_of_range_markers():
    assert citation_coverage("Revenue rose sharply this year. [Source 9]", 3) == 0.0


def test_coverage_each_sentence_cited_inline_after_full_stops():
    answer = "Revenue rose 18 percent in 2025. [Source 1] Costs fell two percent. [Source 2]"
    assert citation_coverage(answer, 3) == 1.0


def test_coverage_prefix_style_markers_on_separate_lines():
    answer = "[Source 1] Revenue rose by ten percent\n[Source 2] Costs fell by two percent"
    assert citation_coverage(answer, 3) == 1.0
