"""The whole API must behave the same when VECTOR_STORE=chroma."""
import pytest

pytest.importorskip("chromadb")

from app.config import get_settings  # noqa: E402
from app.rag import dependencies as deps  # noqa: E402
from app.rag.chroma_store import ChromaVectorStore  # noqa: E402
from tests.conftest import make_pdf  # noqa: E402

REVENUE = "Revenue growth was strong in fiscal year 2025. " * 20
VACATION = "Employees receive twenty vacation days under the company vacation policy. " * 20


class Generator:
    def generate(self, question, context):
        return "Employees get twenty vacation days. [Source 1]"


@pytest.fixture
def chroma_client(client, tmp_path, monkeypatch):
    store = ChromaVectorStore(tmp_path / "chroma-api")
    monkeypatch.setattr(deps, "get_vector_store", lambda: store)
    monkeypatch.setattr(deps, "get_generator", lambda: Generator())
    monkeypatch.setattr(get_settings(), "retrieval_threshold", 0.35)
    client.chroma = store
    return client


def _upload(client, name="report.pdf"):
    pdf = make_pdf([("Finance", REVENUE), ("HR Policy", VACATION)])
    return client.post("/api/documents/upload", files={"file": (name, pdf, "application/pdf")}).json()["id"]


def test_upload_indexes_into_chroma(chroma_client):
    doc_id = _upload(chroma_client)
    doc = chroma_client.get(f"/api/documents/{doc_id}").json()
    assert doc["status"] == "ready" and chroma_client.chroma.count == doc["chunk_count"] > 0


def test_hybrid_search_and_chat_work_on_chroma(chroma_client):
    _upload(chroma_client)
    hits = chroma_client.post("/api/search", json={"query": "vacation policy"}).json()
    assert hits[0]["page_number"] == 2 and hits[0]["dense_score"] is not None
    body = chroma_client.post("/api/chat", json={"question": "How many vacation days do employees get?"}).json()
    assert body["citations"] and body["citations"][0]["document"] == "report.pdf"
    assert body["grounded"] is True


def test_document_filter_and_delete_on_chroma(chroma_client):
    first, second = _upload(chroma_client, "a.pdf"), _upload(chroma_client, "b.pdf")
    only = chroma_client.post("/api/search", json={"query": "revenue", "document_ids": [second]}).json()
    assert only and {h["document_id"] for h in only} == {second}
    assert chroma_client.delete(f"/api/documents/{first}").status_code == 204
    remaining = chroma_client.post("/api/search", json={"query": "revenue", "top_k": 10}).json()
    assert {h["document_id"] for h in remaining} == {second}
