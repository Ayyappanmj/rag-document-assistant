"""Citation handling: find [Source N] markers in an LLM answer, validate them against the
sources that were actually in the context, rewrite them into readable form, and measure coverage."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # type-only import keeps this module lightweight
    from app.rag.hybrid_retriever import HybridResult

# Matches [Source 1], [Sources 1, 2], [Source 1 and 3], [source: 2], (Source 2). The word "source"
# is required, so things like "(2025)" or "[2]" are never mistaken for citations.
_MARKER_RE = re.compile(
    r"[\[(]\s*sources?\s*:?\s*(\d+(?:\s*(?:,|;|&|and)\s*\d+)*)\s*[\])]", re.IGNORECASE
)
_NUM_RE = re.compile(r"\d+")
MIN_WORDS_FOR_CLAIM = 4  # shorter fragments ("Yes.", headings) are not counted as factual claims


@dataclass
class CitationResult:
    answer: str                                   # markers rewritten to [Source: file.pdf, Page N]
    cited_sources: list[HybridResult] = field(default_factory=list)  # unique, in order of first use
    invalid_numbers: list[int] = field(default_factory=list)         # numbers with no matching source
    coverage: float = 0.0                         # share of factual sentences with a valid citation


_STRIP_RE = re.compile(r"\[\s*sources?[^\]]*\]|\(\s*sources?\s*:?\s*\d[^)]*\)", re.IGNORECASE)


def strip_citations(text: str) -> str:
    """Remove citation markers (raw [Source 1] or rewritten [Source: file.pdf, Page 2])."""
    return re.sub(r"[ \t]{2,}", " ", _STRIP_RE.sub("", text)).strip()


def _numbers(group: str) -> list[int]:
    return [int(n) for n in _NUM_RE.findall(group)]


def _tidy(text: str) -> str:
    text = re.sub(r"[ \t]+([.,;:!?])", r"\1", text)  # "word [removed]." -> "word."
    text = re.sub(r"[ \t]{2,}", " ", text)
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


_LEADING_RE = re.compile(r"^(?:" + _MARKER_RE.pattern + r"\s*)+", re.IGNORECASE)
_SPLIT_RE = re.compile(r"(\n+|(?<=[.!?])[ \t]+)")  # newline or sentence end; delimiter is kept


def _valid_numbers(text: str, source_count: int) -> list[int]:
    nums = [n for m in _MARKER_RE.finditer(text) for n in _numbers(m.group(1))]
    return [n for n in nums if 1 <= n <= source_count]


def citation_coverage(answer: str, source_count: int) -> float:
    """Fraction of factual sentences that carry at least one valid [Source N] marker."""
    parts = _SPLIT_RE.split(answer)
    segments: list[list] = []  # [text_without_markers, is_covered]
    for i in range(0, len(parts), 2):
        raw = parts[i].strip()
        same_line = i > 0 and "\n" not in parts[i - 1]
        if raw and same_line and segments:
            # A marker right after a full stop ("... 18%. [Source 1] Next sentence") cites the
            # sentence before it. After a newline it is a prefix for the line it starts instead.
            lead = _LEADING_RE.match(raw)
            if lead:
                if _valid_numbers(raw[: lead.end()], source_count):
                    segments[-1][1] = True
                raw = raw[lead.end():].strip()
        if not raw:
            continue
        covered = bool(_valid_numbers(raw, source_count))
        without = _MARKER_RE.sub("", raw).strip()
        if not without.strip(" .,;:-*•"):
            if segments and covered:
                segments[-1][1] = True
            continue
        segments.append([without, covered])

    claims = [s for s in segments if len(re.findall(r"\w+", s[0])) >= MIN_WORDS_FOR_CLAIM
              and not s[0].endswith(":")]
    if not claims:
        return 1.0 if any(c for _, c in segments) else 0.0
    return sum(1 for _, c in claims if c) / len(claims)


def process_citations(answer: str, sources: list[HybridResult]) -> CitationResult:
    """`sources[0]` must be the chunk that was labelled [Source 1] in the prompt."""
    cited: list[int] = []
    invalid: list[int] = []

    def rewrite(match: re.Match) -> str:
        labels: list[str] = []
        for n in _numbers(match.group(1)):
            if 1 <= n <= len(sources):
                if n not in cited:
                    cited.append(n)
                src = sources[n - 1]
                label = f"[Source: {src.document_name}, Page {src.page_number}]"
                if label not in labels:
                    labels.append(label)
            elif n not in invalid:
                invalid.append(n)  # model cited a source that was never provided: drop the marker
        return " ".join(labels)

    rewritten = _tidy(_MARKER_RE.sub(rewrite, answer))
    rewritten = re.sub(r"(\[Source:[^\]]+\])(?:\s*\1)+", r"\1", rewritten)
    return CitationResult(
        answer=rewritten,
        cited_sources=[sources[n - 1] for n in cited],
        invalid_numbers=invalid,
        coverage=citation_coverage(answer, len(sources)),
    )
