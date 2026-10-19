"""Page-aware chunking. Each page is split on its own so page numbers stay exact."""
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.document_processor import PageText

MIN_CHUNK_CHARS = 20  # drop fragments too small to be useful


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    chunk_index: int
    text: str
    section: str | None = None


class Chunker:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def chunk_pages(self, pages: list[PageText], document_id: str, document_name: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        for page in pages:
            for piece in self._splitter.split_text(page.text):
                piece = piece.strip()
                if len(piece) < MIN_CHUNK_CHARS:
                    continue
                index = len(chunks)
                chunks.append(Chunk(
                    chunk_id=f"{document_id}_{index}",
                    document_id=document_id,
                    document_name=document_name,
                    page_number=page.page_number,
                    chunk_index=index,
                    text=piece,
                    section=page.section,
                ))
        return chunks
