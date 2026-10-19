import pytest

pytest.importorskip("chromadb")

from app.rag.chroma_store import ChromaVectorStore  # noqa: E402
from tests.fakes import FakeEmbeddingService  # noqa: E402
from tests.test_vector_store_contract import add, chunks_for  # noqa: E402

emb = FakeEmbeddingService()


def test_adding_the_same_chunks_twice_does_not_duplicate_them(tmp_path):
    store = ChromaVectorStore(tmp_path)
    chunks = chunks_for("d1", ["alpha beta gamma", "delta epsilon zeta"])
    add(store, chunks)
    add(store, chunks)
    assert store.count == 2


def test_data_is_persisted_in_the_chosen_folder(tmp_path):
    ChromaVectorStore(tmp_path / "chroma-data")
    assert any((tmp_path / "chroma-data").iterdir())


def test_large_documents_are_written_in_batches(tmp_path):
    store = ChromaVectorStore(tmp_path)
    texts = [f"chunk number {i} about topic{i % 13}" for i in range(2300)]  # more than one write batch
    add(store, chunks_for("big", texts))
    assert store.count == 2300
    assert store.delete_document("big") == 2300 and store.count == 0
