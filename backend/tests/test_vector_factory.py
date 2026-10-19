import sys

import pytest

from app.config import Settings
from app.rag.vector_factory import create_vector_store
from app.rag.vector_store import VectorStore


def settings(tmp_path, **kw):
    return Settings(index_dir=str(tmp_path / "idx"), chroma_dir=str(tmp_path / "chroma"), **kw)


def test_faiss_is_the_default(tmp_path):
    store = create_vector_store(settings(tmp_path))
    assert isinstance(store, VectorStore) and store.name == "faiss"


def test_name_is_case_insensitive_and_can_be_overridden(tmp_path):
    assert create_vector_store(settings(tmp_path, vector_store="FAISS")).name == "faiss"
    assert create_vector_store(settings(tmp_path, vector_store="chroma"), name="faiss").name == "faiss"


def test_chroma_is_selected_by_setting(tmp_path):
    pytest.importorskip("chromadb")
    assert create_vector_store(settings(tmp_path, vector_store="chroma")).name == "chroma"


def test_unknown_store_is_rejected_with_the_valid_options(tmp_path):
    with pytest.raises(ValueError, match="faiss, chroma"):
        create_vector_store(settings(tmp_path, vector_store="pinecone"))


def test_missing_chromadb_gives_an_actionable_error(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "app.rag.chroma_store", None)  # makes the import fail
    with pytest.raises(RuntimeError, match="requirements-chroma.txt"):
        create_vector_store(settings(tmp_path, vector_store="chroma"))
