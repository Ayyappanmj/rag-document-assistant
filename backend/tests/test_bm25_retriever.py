import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base, Document, DocumentChunk
from app.rag.bm25_retriever import BM25Retriever, tokenize


def test_tokenize_lowercases_and_drops_stopwords():
    assert tokenize("What was the Revenue?") == ["revenue"]


def test_tokenize_keeps_numbers_whole():
    assert "1,842" in tokenize("Chunks: 1,842")
    assert "3.5" in tokenize("growth of 3.5 percent")
    assert "18" in tokenize("up 18%")


def test_tokenize_splits_letters_and_digits():
    assert tokenize("FY2025") == ["fy", "2025"]


@pytest.fixture
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def add_doc(doc_id, name, texts, status="ready"):
        with Session() as db:
            db.add(Document(id=doc_id, name=name, stored_filename=f"{doc_id}.pdf", status=status))
            db.flush()
            db.add_all(
                DocumentChunk(id=f"{doc_id}_{i}", document_id=doc_id, chunk_index=i,
                              page_number=i + 1, text=t)
                for i, t in enumerate(texts)
            )
            db.commit()

    add_doc("d1", "a.pdf", [
        "Revenue grew 18% in fiscal 2025 driven by cloud services.",
        "The board approved a dividend policy for shareholders.",
        "Security certification ISO 27001 was renewed this year.",
    ])
    add_doc("d2", "b.pdf", ["Employees receive twenty vacation days per year.", "Office locations include Pune and Berlin."])
    return BM25Retriever(Session), add_doc


def test_exact_keyword_ranks_first(env):
    retriever, _ = env
    hit = retriever.search("ISO 27001 certification", top_k=3)[0]
    assert hit.document_name == "a.pdf" and hit.page_number == 3


def test_number_query_matches(env):
    retriever, _ = env
    assert retriever.search("18%", top_k=1)[0].page_number == 1


def test_no_match_returns_empty(env):
    retriever, _ = env
    assert retriever.search("zeppelin", top_k=5) == []


def test_stopword_only_query_returns_empty(env):
    retriever, _ = env
    assert retriever.search("what is the", top_k=5) == []


def test_document_filter(env):
    retriever, _ = env
    hits = retriever.search("year", top_k=5, document_ids=["d2"])
    assert hits and all(h.document_id == "d2" for h in hits)


def test_non_ready_documents_excluded(env):
    retriever, add_doc = env
    add_doc("d3", "c.pdf", ["zeppelin manufacturing details"], status="processing")
    assert retriever.search("zeppelin") == []


def test_invalidate_picks_up_new_documents(env):
    retriever, add_doc = env
    assert retriever.search("zeppelin") == []
    add_doc("d4", "d.pdf", ["zeppelin manufacturing details"])
    assert retriever.search("zeppelin") == []  # stale until invalidated
    retriever.invalidate()
    assert retriever.search("zeppelin")[0].document_name == "d.pdf"


def test_empty_database():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    retriever = BM25Retriever(sessionmaker(bind=engine, autoflush=False, expire_on_commit=False))
    assert retriever.search("anything") == []
