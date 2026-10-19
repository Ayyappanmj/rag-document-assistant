"""Lightweight grounding (hallucination) check. No extra model or paid API needed.

For every factual sentence in the answer we measure how well the retrieved context supports it:
  * lexical support  - share of the sentence's content words that appear in the context
  * semantic support - best cosine similarity to any context sentence/sentence-pair (MiniLM embeddings)
  * numeric check    - every number in the sentence must also appear in the context

This is a fast heuristic, not a formal entailment proof. It catches invented facts, wrong numbers and
off-topic answers, but can miss subtle logical errors. Treat it as a risk signal.
"""
import logging
import re
from dataclasses import dataclass, field

import numpy as np

from app.rag.citation import strip_citations
from app.rag.tokenizer import tokenize

logger = logging.getLogger(__name__)

MAX_CLAIMS = 20
MAX_WINDOWS = 300
MIN_WORDS_FOR_CLAIM = 4
SEM_FLOOR, SEM_CEIL = 0.30, 0.80  # cosine range mapped to 0..1 (unrelated text sits near the floor)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")


@dataclass
class ClaimCheck:
    text: str
    support: float
    supported: bool
    unsupported_numbers: list[str] = field(default_factory=list)


@dataclass
class GroundingResult:
    grounded: bool | None            # None = nothing checkable in the answer
    confidence: float                # 0..1
    faithfulness: float              # share of claims that are supported, 0..1
    claims_checked: int = 0
    unsupported_claims: list[str] = field(default_factory=list)
    unsupported_numbers: list[str] = field(default_factory=list)
    checks: list[ClaimCheck] = field(default_factory=list)


def extract_claims(answer: str) -> list[str]:
    """Split an answer into checkable factual sentences (drops headings, questions, short fragments)."""
    claims: list[str] = []
    for piece in _SENTENCE_SPLIT.split(strip_citations(answer)):
        piece = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", piece).strip()
        if not piece or piece.endswith((":", "?")):
            continue
        if len(re.findall(r"\w+", piece)) < MIN_WORDS_FOR_CLAIM:
            continue
        claims.append(piece)
    return claims[:MAX_CLAIMS]


def extract_numbers(text: str) -> list[str]:
    """Numbers worth verifying: commas removed, single digits ignored ('3 reasons' is not a data point)."""
    out = []
    for raw in _NUM_RE.findall(text):
        n = raw.replace(",", "")
        if len(n.replace(".", "")) >= 2:
            out.append(n)
    return out


def _context_windows(contexts: list[str]) -> list[str]:
    windows: dict[str, None] = {}  # dict = ordered de-duplication
    for ctx in contexts:
        sentences = [s.strip() for s in _SENTENCE_SPLIT.split(ctx) if s.strip()]
        for s in sentences:
            windows[s] = None
        for a, b in zip(sentences, sentences[1:]):
            windows[f"{a} {b}"] = None
    return list(windows)[:MAX_WINDOWS]


class GroundingEvaluator:
    def __init__(self, embedder, support_threshold: float = 0.5, min_faithfulness: float = 0.8):
        self._embedder = embedder
        self.support_threshold = support_threshold
        self.min_faithfulness = min_faithfulness

    def evaluate(self, answer: str, contexts: list[str]) -> GroundingResult:
        claims = extract_claims(answer)
        windows = _context_windows(contexts)
        if not claims or not windows:
            return GroundingResult(grounded=None, confidence=0.0, faithfulness=0.0)

        context_text = " ".join(contexts)
        context_tokens = set(tokenize(context_text))
        context_numbers = set(extract_numbers(context_text))

        window_vecs = self._embedder.embed_texts(windows)
        claim_vecs = self._embedder.embed_texts(claims)
        best_sim = np.max(claim_vecs @ window_vecs.T, axis=1)  # vectors are normalised -> cosine

        checks: list[ClaimCheck] = []
        for claim, sim in zip(claims, best_sim):
            tokens = tokenize(claim)
            lexical = sum(t in context_tokens for t in tokens) / len(tokens) if tokens else 0.0
            semantic = float(np.clip((sim - SEM_FLOOR) / (SEM_CEIL - SEM_FLOOR), 0.0, 1.0))
            bad_numbers = [n for n in extract_numbers(claim) if n not in context_numbers]
            support = 0.0 if bad_numbers else 0.5 * lexical + 0.5 * semantic
            checks.append(ClaimCheck(claim, round(support, 3), support >= self.support_threshold, bad_numbers))

        faithfulness = sum(c.supported for c in checks) / len(checks)
        avg_support = sum(c.support for c in checks) / len(checks)
        bad_numbers_all = [n for c in checks for n in c.unsupported_numbers]
        # A single invented number is enough to fail, even if most sentences are fine.
        grounded = faithfulness >= self.min_faithfulness and not bad_numbers_all
        result = GroundingResult(
            grounded=grounded,
            confidence=round(0.5 * faithfulness + 0.5 * avg_support, 3),
            faithfulness=round(faithfulness, 3),
            claims_checked=len(checks),
            unsupported_claims=[c.text for c in checks if not c.supported],
            unsupported_numbers=bad_numbers_all,
            checks=checks,
        )
        logger.info(
            "grounding_checked claims=%d faithfulness=%.2f confidence=%.2f grounded=%s unsupported_numbers=%d",
            len(checks), result.faithfulness, result.confidence, grounded, len(bad_numbers_all),
        )
        return result

    def answer_relevance(self, question: str, answer: str) -> float:
        """Cosine similarity between the question and the answer text (0..1)."""
        text = strip_citations(answer)
        if not text.strip():
            return 0.0
        q = self._embedder.embed_query(question)
        a = self._embedder.embed_texts([text])[0]
        return float(np.clip(np.dot(q, a), 0.0, 1.0))
