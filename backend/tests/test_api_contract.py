"""Checks the public API against the project specification."""
import re

import pytest

from app.config import get_settings
from app.rag import dependencies as deps
from tests.conftest import make_pdf

REQUIRED_ENDPOINTS = {
    ("post", "/api/documents/upload"),
    ("get", "/api/documents"),
    ("get", "/api/documents/{document_id}"),
    ("delete", "/api/documents/{document_id}"),
    ("post", "/api/chat"),
    ("get", "/api/conversations"),
    ("get", "/api/conversations/{conversation_id}"),
    ("delete", "/api/conversations/{conversation_id}"),
    ("post", "/api/evaluate"),
    ("get", "/api/evaluation/metrics"),
    ("get", "/api/health"),
}

REVENUE = "Revenue growth was strong in fiscal year 2025. " * 20
VACATION = "Employees receive twenty vacation days under the company vacation policy. " * 20


class CitesEverything:
    """Cites every [Source N] it was given, so multi-document behaviour is deterministic."""
    def generate(self, question, context):
        numbers = re.findall(r"\[Source (\d+)\]", context)
        return "The documents discuss revenue growth. " + "".join(f"[Source {n}]" for n in numbers)


@pytest.fixture
def gen(monkeypatch):
    monkeypatch.setattr(get_settings(), "retrieval_threshold", 0.35)
    monkeypatch.setattr(deps, "get_generator", lambda: CitesEverything())


def _upload(client, name):
    pdf = make_pdf([("Finance", REVENUE), ("HR Policy", VACATION)])
    return client.post("/api/documents/upload", files={"file": (name, pdf, "application/pdf")}).json()["id"]


def test_all_specified_endpoints_exist_in_the_openapi_schema(client):
    paths = client.get("/openapi.json").json()["paths"]
    missing = {(m, p) for m, p in REQUIRED_ENDPOINTS if m not in paths.get(p, {})}
    assert not missing, f"missing endpoints: {missing}"


def test_swagger_and_redoc_pages_load(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200


def test_chat_response_matches_the_specified_shape(client, gen):
    _upload(client, "report.pdf")
    body = client.post("/api/chat", json={"question": "revenue growth in fiscal year 2025"}).json()
    assert {"answer", "grounded", "confidence", "citations", "metrics"} <= set(body)
    assert {"document", "page", "chunk_id", "text", "score", "retrieval_type"} <= set(body["citations"][0])
    assert {"retrieval_time_ms", "generation_time_ms", "total_time_ms"} <= set(body["metrics"])
    assert body["metrics"]["total_time_ms"] >= body["metrics"]["retrieval_time_ms"]


def test_multi_document_answers_cite_every_document(client, gen):
    _upload(client, "a.pdf")
    _upload(client, "b.pdf")
    body = client.post("/api/chat", json={"question": "revenue growth in fiscal year 2025", "top_k": 6}).json()
    assert {c["document"] for c in body["citations"]} == {"a.pdf", "b.pdf"}
    assert "[Source: a.pdf" in body["answer"] or "[Source: b.pdf" in body["answer"]


def test_chunk_endpoint_pagination(client):
    doc_id = _upload(client, "report.pdf")
    everything = client.get(f"/api/documents/{doc_id}/chunks", params={"limit": 200}).json()
    page_two = client.get(f"/api/documents/{doc_id}/chunks", params={"page": 2}).json()
    first_only = client.get(f"/api/documents/{doc_id}/chunks", params={"limit": 1}).json()
    skipped = client.get(f"/api/documents/{doc_id}/chunks", params={"limit": 1, "offset": 1}).json()
    assert len(everything) > 1 and len(first_only) == 1
    assert skipped[0]["id"] == everything[1]["id"]
    assert page_two and all(c["page_number"] == 2 for c in page_two)
    assert client.get(f"/api/documents/{doc_id}/chunks", params={"limit": 0}).status_code == 422


@pytest.mark.parametrize("payload", [
    {"query": "x", "top_k": 0}, {"query": "x", "top_k": 99}, {"query": "x", "mode": "magic"}, {"query": ""},
])
def test_search_rejects_invalid_input(client, payload):
    assert client.post("/api/search", json=payload).status_code == 422


def test_http_status_codes_for_missing_resources(client):
    for path in ("/api/documents/nope", "/api/conversations/nope"):
        assert client.get(path).status_code == 404
        assert client.delete(path).status_code == 404


def test_end_to_end_smoke(client, gen):
    """Upload -> ready -> search -> chat -> inspect -> delete."""
    doc_id = _upload(client, "report.pdf")
    doc = client.get(f"/api/documents/{doc_id}").json()
    assert doc["status"] == "ready" and doc["page_count"] == 2 and doc["chunk_count"] > 0

    assert client.post("/api/search", json={"query": "vacation policy"}).json()[0]["page_number"] == 2

    chat = client.post("/api/chat", json={"question": "What does the company vacation policy say?"}).json()
    assert chat["citations"] and chat["grounded"] in (True, False)

    detail = client.get(f"/api/conversations/{chat['conversation_id']}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert client.get("/api/dashboard/stats").json()["questions_asked"] == 1

    assert client.delete(f"/api/documents/{doc_id}").status_code == 204
    assert client.post("/api/search", json={"query": "vacation policy"}).json() == []
