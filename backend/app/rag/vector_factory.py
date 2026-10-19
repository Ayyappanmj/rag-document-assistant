"""Chooses the vector database from the VECTOR_STORE setting."""
from app.config import Settings
from app.rag.vector_store import VectorStore
from app.rag.vector_types import VectorIndex

SUPPORTED = ("faiss", "chroma")


def create_vector_store(settings: Settings, name: str | None = None) -> VectorIndex:
    kind = (name or settings.vector_store).strip().lower()
    if kind == "faiss":
        return VectorStore(settings.index_dir)
    if kind == "chroma":
        try:
            from app.rag.chroma_store import ChromaVectorStore
        except ImportError as exc:
            raise RuntimeError(
                "VECTOR_STORE=chroma needs the chromadb package. Install it with: pip install -r requirements-chroma.txt"
            ) from exc
        return ChromaVectorStore(settings.chroma_dir)
    raise ValueError(f"Unsupported VECTOR_STORE: {kind!r} (use one of: {', '.join(SUPPORTED)})")
