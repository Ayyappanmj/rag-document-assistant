import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base, Document, DocumentChunk
from app.rag.vector_store import VectorStore
from app.services.vector_benchmark import (
    CHUNKS_PER_DOC, compare_on_real_documents, exact_top_k, make_dataset, run_benchmark,
)
from tests.fakes import FakeEmbeddingService


def factories():
    makers = {"faiss": lambda path: VectorStore(path)}
    try:
        from app.rag.chroma_store import ChromaVectorStore
        makers["chroma"] = lambda path: ChromaVectorStore(path)
    except ImportError:
        pass
    return makers


def test_dataset_is_deterministic_and_normalised():
    chunks, vectors, queries = make_dataset(vectors=250, dimension=16, queries=5, seed=7)
    again = make_dataset(vectors=250, dimension=16, queries=5, seed=7)
    assert np.array_equal(vectors, again[1]) and np.array_equal(queries, again[2])
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5)
    assert len(chunks) == 250 and chunks[0].document_id == "doc0" and chunks[CHUNKS_PER_DOC].document_id == "doc1"


def test_exact_top_k_matches_a_plain_sort():
    _, vectors, queries = make_dataset(vectors=200, dimension=16, queries=4, seed=1)
    ids = [f"c{i}" for i in range(200)]
    expected = [[ids[j] for j in np.argsort(-(q @ vectors.T))[:5]] for q in queries]
    assert exact_top_k(vectors, queries, ids, 5) == expected


def test_full_benchmark_has_the_expected_shape_and_faiss_is_exact(tmp_path):
    result = run_benchmark(factories(), tmp_path, vectors=300, dimension=32, queries=10, top_k=5, seed=3)
    assert result["label"] == "Vector store benchmark" and "one machine" in result["note"]
    assert result["parameters"]["vectors"] == 300
    faiss_result = result["stores"]["faiss"]
    assert faiss_result["recall_at_k"] == 1.0            # flat search is exact
    assert faiss_result["filtered_recall_at_k"] == 1.0 and faiss_result["filter_correct"] is True
    assert faiss_result["reopened_vectors"] == 300
    assert faiss_result["deleted_vectors"] == CHUNKS_PER_DOC
    for key in ("build_seconds", "disk_mb", "open_seconds", "delete_document_ms"):
        assert faiss_result[key] >= 0
    assert {"mean", "p50", "p95"} == set(faiss_result["query_ms"])


def test_chroma_results_when_installed(tmp_path):
    pytest.importorskip("chromadb")
    chroma = run_benchmark(factories(), tmp_path, vectors=300, dimension=32, queries=10, top_k=5, seed=3)["stores"]["chroma"]
    assert chroma["index_type"].startswith("HNSW")
    assert chroma["recall_at_k"] >= 0.9 and chroma["filter_correct"] is True
    assert chroma["reopened_vectors"] == 300 and chroma["deleted_vectors"] == CHUNKS_PER_DOC


def test_missing_optional_dependency_is_reported_not_raised(tmp_path):
    def broken(path):
        raise ImportError("chromadb is not installed")

    result = run_benchmark({"faiss": factories()["faiss"], "chroma": broken}, tmp_path, vectors=120, dimension=16,
                           queries=5, top_k=3, seed=1)
    assert result["stores"]["chroma"] == {"error": "chromadb is not installed"}
    assert result["stores"]["faiss"]["recall_at_k"] == 1.0


def test_real_document_comparison(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    data = {
        ("d1", "a.pdf"): ["Revenue grew eighteen percent in fiscal 2025.", "The board approved a dividend policy."],
        ("d2", "b.pdf"): ["Employees receive twenty vacation days per year.", "Passwords need fourteen characters."],
    }
    with Session() as db:
        for (doc_id, name), texts in data.items():
            db.add(Document(id=doc_id, name=name, stored_filename=f"{doc_id}.pdf", status="ready"))
            db.flush()
            db.add_all(DocumentChunk(id=f"{doc_id}_{i}", document_id=doc_id, chunk_index=i, page_number=i + 1, text=t)
                       for i, t in enumerate(texts))
        db.commit()
        questions = [
            {"question": "revenue grew eighteen percent", "expected_sources": ["a.pdf"]},
            {"question": "how many vacation days do employees receive", "expected_sources": ["b.pdf"]},
            {"question": "who approved the dividend policy", "expected_sources": []},
        ]
        out = compare_on_real_documents(db, FakeEmbeddingService(), questions, ["d1", "d2"], 1, factories(), tmp_path)
    assert out["questions"] == 3
    for stats in out["stores"].values():
        assert stats["retrieval_precision"] == 1.0 and stats["retrieval_recall"] == 1.0
        assert stats["vectors"] == 4 and stats["avg_query_ms"] >= 0
    if len(out["stores"]) == 2:
        assert out["top_k_overlap_jaccard"] == 1.0
    else:
        assert out["top_k_overlap_jaccard"] is None
