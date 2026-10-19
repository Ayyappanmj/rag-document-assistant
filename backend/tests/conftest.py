import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.main import app
from app.rag import dependencies as deps
from app.rag.bm25_retriever import BM25Retriever
from app.rag.vector_store import VectorStore
from tests.fakes import FakeEmbeddingService
from app.models.database import Base, get_db, get_session_factory


@pytest.fixture
def vector_store(tmp_path):
    return VectorStore(tmp_path / "index")


@pytest.fixture
def client(tmp_path, monkeypatch, vector_store):
    """TestClient with an in-memory DB and a temporary upload folder."""
    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path))
    fake_embedder = FakeEmbeddingService()  # no model download in tests
    monkeypatch.setattr(deps, "get_embedding_service", lambda: fake_embedder)
    monkeypatch.setattr(deps, "get_vector_store", lambda: vector_store)
    from app.rag.reranker import ReRanker
    monkeypatch.setattr(deps, "get_reranker", lambda: ReRanker(enabled=False))
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    bm25 = BM25Retriever(Session)
    monkeypatch.setattr(deps, "get_bm25_retriever", lambda: bm25)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_session_factory] = lambda: Session
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_pdf(pages: list[tuple[str, str]]) -> bytes:
    """Build a small real PDF. Each page is (heading, body_text)."""
    import fitz

    doc = fitz.open()
    for heading, body in pages:
        page = doc.new_page()
        if heading:
            page.insert_text((72, 80), heading, fontsize=22)
        if body:
            page.insert_textbox(fitz.Rect(72, 110, 520, 780), body, fontsize=11)
    data = doc.tobytes()
    doc.close()
    return data
