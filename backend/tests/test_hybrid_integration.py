import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base, Document, DocumentChunk
from app.rag.bm25_retriever import BM25Retriever
from app.rag.chunker import Chunk
from app.rag.hybrid_retriever import HybridRetriever
from app.rag.vector_store import VectorStore
from tests.fakes import FakeEmbeddingService

DATA = [
    ("docA", "a.pdf", 1, "Revenue grew 18 percent in fiscal 2025 driven by cloud services."),
    ("docA", "a.pdf", 2, "The board approved a dividend policy for shareholders."),
    ("docA", "a.pdf", 3, "Security certification ISO 27001 was renewed this year."),
    ("docB", "b.pdf", 1, "Employees receive twenty vacation days per year."),
    ("docB", "b.pdf", 2, "Office locations include Pune and Berlin."),
]


@pytest.fixture
def parts(tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    embedder, store = FakeEmbeddingService(), VectorStore(tmp_path)

    chunks = [Chunk(f"{d}_{i}", d, n, p, i, t) for i, (d, n, p, t) in enumerate(DATA)]
    with Session() as db:
        for doc_id, name in {(d, n) for d, n, _, _ in DATA}:
            db.add(Document(id=doc_id, name=name, stored_filename=f"{doc_id}.pdf", status="ready"))
        db.flush()
        db.add_all(
            DocumentChunk(id=c.chunk_id, document_id=c.document_id, chunk_index=c.chunk_index,
                          page_number=c.page_number, text=c.text)
            for c in chunks
        )
        db.commit()
    store.add(chunks, embedder.embed_texts([c.text for c in chunks]))
    return embedder, store, BM25Retriever(Session)


def _retriever(parts, dense=0.7, bm25=0.3):
    embedder, store, bm25_retriever = parts
    return HybridRetriever(embedder, store, bm25_retriever, dense, bm25)


def test_exact_keyword_query_finds_the_right_chunk_with_both_scores(parts):
    top = _retriever(parts).retrieve("ISO 27001 certification", top_k=3)[0]
    assert (top.document_name, top.page_number) == ("a.pdf", 3)
    assert top.dense_score is not None and top.bm25_score is not None


def test_query_matching_another_document_ranks_it_first(parts):
    top = _retriever(parts).retrieve("vacation days for employees", top_k=3)[0]
    assert top.document_name == "b.pdf"


def test_document_filter_applies_to_both_retrievers(parts):
    results = _retriever(parts).retrieve("revenue vacation policy", top_k=10, document_ids=["docB"])
    assert results and {r.document_id for r in results} == {"docB"}


@pytest.mark.parametrize("dense,bm25", [(1.0, 0.0), (0.0, 1.0), (0.5, 0.5)])
def test_every_weighting_still_finds_the_exact_match(parts, dense, bm25):
    top = _retriever(parts, dense, bm25).retrieve("ISO 27001", top_k=1)[0]
    assert top.page_number == 3 and top.document_name == "a.pdf"


def test_fused_scores_are_between_zero_and_one_and_sorted(parts):
    results = _retriever(parts).retrieve("revenue cloud services", top_k=5)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
    assert all(0.0 <= s <= 1.0 for s in scores)
