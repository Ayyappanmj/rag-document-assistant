import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.database import Base, Document, DocumentChunk
from app.rag.vector_store import VectorStore
from app.services.reindex_service import reindex_documents
from tests.fakes import FakeEmbeddingService

emb = FakeEmbeddingService()


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with Session() as session:
        for doc_id, name, status, texts in [
            ("d1", "a.pdf", "ready", ["Revenue grew eighteen percent.", "The board approved a dividend."]),
            ("d2", "b.pdf", "ready", ["Employees receive twenty vacation days."]),
            ("d3", "c.pdf", "failed", ["This text must never be indexed."]),
        ]:
            session.add(Document(id=doc_id, name=name, stored_filename=f"{doc_id}.pdf", status=status))
            session.flush()
            session.add_all(
                DocumentChunk(id=f"{doc_id}_{i}", document_id=doc_id, chunk_index=i, page_number=i + 1,
                              section="Intro" if i == 0 else None, text=t)
                for i, t in enumerate(texts)
            )
        session.commit()
        yield session


def stores(tmp_path):
    out = [VectorStore(tmp_path / "faiss")]
    try:
        from app.rag.chroma_store import ChromaVectorStore
        out.append(ChromaVectorStore(tmp_path / "chroma"))
    except ImportError:
        pass
    return out


def test_rebuilds_every_ready_document_into_each_store(db, tmp_path):
    for store in stores(tmp_path):
        result = reindex_documents(db, emb, store)
        assert result == {"documents": 2, "chunks": 3, "store": store.name}
        assert store.count == 3
        hit = store.search(emb.embed_query("vacation days"), top_k=1)[0]
        assert (hit.document_name, hit.page_number) == ("b.pdf", 1)


def test_failed_documents_are_skipped(db, tmp_path):
    for store in stores(tmp_path):
        reindex_documents(db, emb, store)
        texts = {h.text for h in store.search(emb.embed_query("This text must never be indexed"), top_k=10)}
        assert "This text must never be indexed." not in texts


def test_running_it_twice_does_not_duplicate_vectors(db, tmp_path):
    for store in stores(tmp_path):
        reindex_documents(db, emb, store)
        reindex_documents(db, emb, store)
        assert store.count == 3


def test_sections_survive_the_round_trip(db, tmp_path):
    for store in stores(tmp_path):
        reindex_documents(db, emb, store)
        top = store.search(emb.embed_query("Revenue grew eighteen percent"), top_k=1)[0]
        assert top.section == "Intro"
