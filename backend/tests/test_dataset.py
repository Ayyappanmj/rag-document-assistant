"""Checks that the shipped evaluation dataset matches the fictional sample documents."""
import importlib.util
import sys
from pathlib import Path

import pytest

from app.rag.evaluator import extract_numbers

EVAL_DIR = Path(__file__).resolve().parents[2] / "evaluation"
pytestmark = pytest.mark.skipif(not (EVAL_DIR / "questions.json").exists(), reason="evaluation/ folder not present")

REQUIRED_TYPES = {"factual", "multi_hop", "numerical", "comparison", "unanswerable"}
DERIVED_NUMBERS = {"38.9", "29"}  # computed answers (46% of 84.6; 24 + 5), not quoted from a document


def _load(name: str):
    sys.path.insert(0, str(EVAL_DIR))
    try:
        spec = importlib.util.spec_from_file_location(name, EVAL_DIR / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(EVAL_DIR))


@pytest.fixture(scope="module")
def questions():
    import json
    return json.loads((EVAL_DIR / "questions.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def sample_docs():
    return _load("sample_content").SAMPLE_DOCS


def test_dataset_shape(questions, sample_docs):
    assert len(questions) >= 15
    assert len({q["id"] for q in questions}) == len(questions)
    assert {q["type"] for q in questions} == REQUIRED_TYPES
    for q in questions:
        assert q["question"].strip() and q["ground_truth"].strip()
        if q["answerable"]:
            assert q["expected_sources"] and set(q["expected_sources"]) <= set(sample_docs)
        else:
            assert q["expected_sources"] == []


def test_numbers_in_ground_truth_come_from_the_expected_documents(questions, sample_docs):
    for q in questions:
        if not q["answerable"]:
            continue
        text = " ".join(body for name in q["expected_sources"] for _, body in sample_docs[name])
        doc_numbers = set(extract_numbers(text))
        for number in extract_numbers(q["ground_truth"]):
            assert number in doc_numbers or number in DERIVED_NUMBERS, f"{q['id']}: {number} not in sources"


def test_sample_pdfs_build_and_extract(tmp_path, sample_docs):
    maker = _load("make_sample_pdfs")
    from app.rag.document_processor import DocumentProcessor

    for name, pages in sample_docs.items():
        path = tmp_path / name
        path.write_bytes(maker.build_pdf(pages))
        result = DocumentProcessor().extract(path)
        assert result.page_count == len(pages)
        for page, (_, body) in zip(result.pages, pages):
            assert set(extract_numbers(body)) <= set(extract_numbers(page.text))
