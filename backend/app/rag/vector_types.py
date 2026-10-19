"""What every vector database backend must provide, so FAISS and Chroma are interchangeable."""
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from app.rag.chunker import Chunk


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section: str | None
    text: str
    score: float  # cosine similarity (vectors are normalised)


class VectorIndex(Protocol):
    name: str          # "faiss" or "chroma"
    index_type: str    # human-readable, shown in the comparison

    @property
    def count(self) -> int: ...

    def add(self, chunks: list[Chunk], embeddings: np.ndarray) -> None: ...

    def search(
        self, query_vec: np.ndarray, top_k: int = 5, document_ids: list[str] | None = None
    ) -> list[SearchResult]: ...

    def delete_document(self, document_id: str) -> int: ...
