from app.rag.context_builder import build_context
from app.rag.hybrid_retriever import HybridResult


def hr(i, text, section=None, page=1):
    return HybridResult(f"c{i}", "d", "Annual_Report.pdf", page, section, text, 0.5, 0.5, None)


def test_numbered_sources_with_document_and_page():
    ctx = build_context([hr(1, "Revenue rose.", page=42), hr(2, "Costs fell.", section="Costs", page=43)])
    assert "[Source 1] Annual_Report.pdf, Page 42\nRevenue rose." in ctx.text
    assert "[Source 2] Annual_Report.pdf, Page 43, Section: Costs" in ctx.text
    assert len(ctx.sources) == 2


def test_budget_drops_lower_ranked_chunks_and_keeps_numbering_aligned():
    ctx = build_context([hr(1, "a" * 100), hr(2, "b" * 100), hr(3, "c" * 100)], max_chars=300)
    assert [s.chunk_id for s in ctx.sources] == ["c1", "c2"]
    assert "[Source 3]" not in ctx.text


def test_first_chunk_trimmed_not_dropped():
    ctx = build_context([hr(1, "a" * 500)], max_chars=100)
    assert len(ctx.sources) == 1 and len(ctx.text) == 100


def test_empty_results():
    ctx = build_context([])
    assert ctx.text == "" and ctx.sources == []
