"""Rebuild a vector index from the database.

Run from the backend/ folder with the virtual environment active, and stop the server first:

    python -m app.scripts.reindex                  # rebuild the store selected by VECTOR_STORE
    python -m app.scripts.reindex --store chroma   # fill Chroma (after installing requirements-chroma.txt)
    python -m app.scripts.reindex --store faiss
"""
import argparse

from app.config import get_settings
from app.core.logging import setup_logging
from app.models.database import SessionLocal, init_db
from app.rag.embeddings import EmbeddingService
from app.rag.vector_factory import SUPPORTED, create_vector_store
from app.services.reindex_service import reindex_documents


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild a vector index from the chunks in the database")
    parser.add_argument("--store", choices=SUPPORTED, help="which vector database to fill (default: VECTOR_STORE)")
    args = parser.parse_args()

    settings = get_settings()
    setup_logging("WARNING")
    init_db()
    store = create_vector_store(settings, args.store)
    embedder = EmbeddingService(settings.embedding_model, settings.embedding_batch_size)

    print(f"Rebuilding the {store.name} index (the first run downloads the embedding model)...")
    with SessionLocal() as db:
        result = reindex_documents(db, embedder, store)
    print(f"Done: {result['chunks']} chunks from {result['documents']} documents are now in {store.name} "
          f"({store.count} vectors in total).")
    print("Restart the backend so it opens the updated index.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
