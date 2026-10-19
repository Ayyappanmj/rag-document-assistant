from app.rag.chunker import Chunker
from app.rag.document_processor import PageText

TEXT = " ".join(f"word{i}" for i in range(200))


def test_consecutive_chunks_overlap():
    chunks = Chunker(chunk_size=200, chunk_overlap=60).chunk_pages([PageText(1, TEXT)], "d", "a.pdf")
    assert len(chunks) > 3
    for first, second in zip(chunks, chunks[1:]):
        assert set(first.text.split()[-4:]) & set(second.text.split()), "no shared words between neighbours"


def test_tiny_fragments_and_empty_input_are_dropped():
    chunker = Chunker(200, 40)
    assert chunker.chunk_pages([], "d", "a.pdf") == []
    assert chunker.chunk_pages([PageText(1, "Hi")], "d", "a.pdf") == []


def test_chunk_ids_belong_to_the_document_and_continue_across_pages():
    pages = [PageText(1, TEXT), PageText(2, TEXT)]
    chunks = Chunker(200, 40).chunk_pages(pages, "docABC", "a.pdf")
    assert all(c.chunk_id.startswith("docABC_") for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    first_page2 = next(c for c in chunks if c.page_number == 2)
    assert first_page2.chunk_index > 0  # numbering did not restart on page 2


def test_pages_are_never_mixed_inside_one_chunk():
    pages = [PageText(1, "alpha " * 50), PageText(2, "omega " * 50)]
    for chunk in Chunker(1000, 100).chunk_pages(pages, "d", "a.pdf"):
        assert ("alpha" in chunk.text) != ("omega" in chunk.text)


def test_missing_section_stays_none():
    chunk = Chunker(200, 40).chunk_pages([PageText(1, TEXT)], "d", "a.pdf")[0]
    assert chunk.section is None
