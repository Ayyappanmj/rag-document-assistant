"""Turns retrieved chunks into a numbered context block for the LLM prompt."""
from dataclasses import dataclass

from app.rag.hybrid_retriever import HybridResult


@dataclass
class BuiltContext:
    text: str
    sources: list[HybridResult]  # sources[0] is "[Source 1]" in the text, and so on


def build_context(results: list[HybridResult], max_chars: int = 6000) -> BuiltContext:
    """Results must be ordered best-first; lower-ranked chunks are dropped once the budget is full."""
    parts: list[str] = []
    used: list[HybridResult] = []
    total = 0
    for r in results:
        header = f"[Source {len(used) + 1}] {r.document_name}, Page {r.page_number}"
        if r.section:
            header += f", Section: {r.section}"
        block = f"{header}\n{r.text}"
        cost = len(block) + (2 if parts else 0)  # 2 = blank-line separator
        if total + cost > max_chars:
            if parts:
                break
            block = block[:max_chars]  # always keep the best chunk, even if it must be trimmed
            cost = len(block)
        parts.append(block)
        used.append(r)
        total += cost
    return BuiltContext(text="\n\n".join(parts), sources=used)
