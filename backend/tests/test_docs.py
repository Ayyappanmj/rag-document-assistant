"""Keeps the README and portfolio text honest and complete."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not (ROOT / "README.md").exists(), reason="not a full checkout")


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


README_SECTIONS = [
    "Overview", "Features", "Architecture", "Tech stack", "How RAG works", "Hybrid search", "Citation system",
    "Hallucination protection", "Evaluation metrics", "Project structure", "Installation", "Environment variables",
    "Running locally", "Running with Ollama", "Running tests", "Docker setup", "Deployment", "Screenshots",
    "API documentation", "Future improvements", "License",
]


def test_readme_has_every_required_section_and_a_mermaid_diagram():
    headings = re.findall(r"^#{1,3} (.+)$", read("README.md"), re.M)
    for section in README_SECTIONS:
        assert any(h.lower().startswith(section.lower()) for h in headings), f"README is missing: {section}"
    assert "```mermaid" in read("README.md")


def test_readme_has_the_required_badges():
    readme = read("README.md").lower()
    for badge in ("python", "fastapi", "next.js", "typescript", "faiss", "rag", "docker", "vercel"):
        assert f"img.shields.io/badge/{badge}" in readme, f"missing badge: {badge}"


def test_readme_does_not_claim_benchmark_numbers():
    readme = read("README.md")
    assert "not benchmark" in readme and "heuristic" in readme.lower()
    section = readme.split("## Evaluation metrics")[1].split("## Project structure")[0]
    assert not re.search(r"\d+(\.\d+)?\s*%", section), "do not publish unmeasured percentages"


def test_every_mentioned_file_exists():
    readme = read("README.md")
    for rel in ("DOCKER.md", "docs/ARCHITECTURE.md", "docs/DEPLOYMENT.md", "LICENSE", ".env.example"):
        assert rel in readme and (ROOT / rel).exists(), rel


PORTFOLIO_KEYWORDS = [
    "RAG", "LLM", "NLP", "FAISS", "BM25", "Vector Search", "Hybrid Search", "Semantic Search", "Python", "FastAPI",
    "Next.js", "Sentence Transformers", "Prompt Engineering", "Hallucination Detection", "Evaluation", "REST API",
    "Docker", "Vercel",
]


def test_portfolio_text_has_three_bullets_and_all_keywords_and_no_invented_numbers():
    text = read("docs/PORTFOLIO.md")
    bullets_section = text.split("## Resume bullet points")[1].split("##")[0]
    bullets = [l for l in bullets_section.splitlines() if l.startswith("- ")]
    assert len(bullets) == 3
    assert not re.search(r"\d+(\.\d+)?\s*%", bullets_section), "resume bullets must not contain percentages"
    lowered = text.lower()
    for keyword in PORTFOLIO_KEYWORDS:
        assert keyword.lower() in lowered, f"missing keyword: {keyword}"
    assert "Production-grade Retrieval-Augmented Generation platform for intelligent PDF question answering" in text


def test_deployment_guide_covers_the_required_limitations():
    guide = read("docs/DEPLOYMENT.md").lower()
    for topic in ("ephemeral filesystem", "faiss", "model storage", "cpu and ram", "request timeouts", "cold starts"):
        assert topic in guide, f"deployment guide does not cover: {topic}"
    assert "root directory" in guide and "next_public_api_url" in guide and "cors_origins" in guide
    assert "no authentication" in guide or "no login" in guide


def test_vector_store_guide_is_honest_and_complete():
    guide = read("docs/VECTOR_STORES.md")
    lowered = guide.lower()
    for needle in ("faiss", "chroma", "vector_store=chroma", "python -m app.scripts.reindex",
                   "compare_vector_stores.py", "hypotheses", "not results", "one machine"):
        assert needle in lowered, f"VECTOR_STORES.md is missing: {needle}"
    assert not re.search(r"\d+(\.\d+)?\s*%", guide), "do not publish unmeasured percentages"
    assert "docs/VECTOR_STORES.md" in read("README.md")
