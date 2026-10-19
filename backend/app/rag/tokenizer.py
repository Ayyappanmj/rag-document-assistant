"""Shared tokenizer used by BM25 retrieval and the grounding evaluator."""
import re

# Numbers (incl. 3.5 / 1,842) stay whole; letters and digits split, so "FY2025" -> "fy", "2025".
_TOKEN_RE = re.compile(r"\d+(?:[.,]\d+)*|[a-z]+")
_STOPWORDS = frozenset(
    "a an and are as at be by for from has have in is it its of on or that the this to was were what when "
    "which who will with".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]
