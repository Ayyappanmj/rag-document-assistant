import pytest

from app.rag.chunker import Chunker
from app.rag.document_processor import PageText

LONG = " ".join(f"Sentence number {i} talks about revenue." for i in range(60))


def test_chunks_respect_size_and_keep_page_numbers():
    pages = [PageText(1, LONG, "Intro"), PageText(2, LONG, "Results")]
    chunks = Chunker(chunk_size=200, chunk_overlap=40).chunk_pages(pages, "doc1", "report.pdf")
    assert len(chunks) > 4
    assert all(len(c.text) <= 200 for c in chunks)
    assert {c.page_number for c in chunks} == {1, 2}
    assert all(c.document_name == "report.pdf" for c in chunks)
    assert chunks[0].section == "Intro" and chunks[-1].section == "Results"


def test_chunk_ids_unique_and_sequential():
    chunks = Chunker(200, 40).chunk_pages([PageText(1, LONG)], "doc1", "r.pdf")
    ids = [c.chunk_id for c in chunks]
    assert len(set(ids)) == len(ids)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        Chunker(chunk_size=100, chunk_overlap=100)
