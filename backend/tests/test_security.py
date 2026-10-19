import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.rag import dependencies as deps
from app.rag.generator import LLMError, OpenAICompatibleClient
from tests.conftest import make_pdf

PDF = make_pdf([("Finance", "Revenue growth was strong in fiscal year 2025. " * 20)])
VACATION = "Employees receive twenty vacation days under the company vacation policy. " * 20


def test_upload_filename_cannot_escape_the_upload_folder(client, tmp_path):
    r = client.post("/api/documents/upload", files={"file": ("../../evil.pdf", PDF, "application/pdf")})
    assert r.status_code == 201
    assert r.json()["name"] == "evil.pdf"                       # directories are stripped
    assert not (tmp_path.parent / "evil.pdf").exists()
    assert all(p.parent == tmp_path for p in tmp_path.glob("*.pdf"))


def test_stored_files_never_use_the_client_supplied_name(client, tmp_path):
    client.post("/api/documents/upload", files={"file": ("my report.pdf", PDF, "application/pdf")})
    assert not (tmp_path / "my report.pdf").exists()            # random UUID name on disk instead


def test_rejected_upload_leaves_no_file_behind(client, tmp_path):
    client.post("/api/documents/upload", files={"file": ("fake.pdf", b"not a pdf", "application/pdf")})
    assert list(tmp_path.glob("*.pdf")) == []


def test_cors_allows_the_configured_origin_only(client):
    allowed = get_settings().cors_origin_list[0]
    ok = client.options("/api/health", headers={"Origin": allowed, "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == allowed
    bad = client.options(
        "/api/health", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"}
    )
    assert "access-control-allow-origin" not in bad.headers


def test_unexpected_errors_return_a_generic_message(client, monkeypatch):
    def boom():
        raise RuntimeError("database password is hunter2")

    monkeypatch.setattr(deps, "get_hybrid_retriever", boom)
    quiet = TestClient(app, raise_server_exceptions=False)
    r = quiet.post("/api/search", json={"query": "anything"})
    assert r.status_code == 500
    assert r.json() == {"detail": "Internal server error."}
    assert "hunter2" not in r.text and "Traceback" not in r.text


def test_oversized_question_is_rejected(client):
    assert client.post("/api/chat", json={"question": "x" * 2001}).status_code == 422


def test_sql_injection_style_ids_are_just_not_found(client):
    assert client.get("/api/conversations/%27%20OR%201%3D1%20--").status_code == 404
    assert client.get("/api/documents/%27%3B%20DROP%20TABLE%20documents%3B--").status_code == 404


def test_config_endpoint_exposes_no_secrets(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "openai_api_key", "sk-super-secret")
    monkeypatch.setattr(get_settings(), "secret_key", "jwt-super-secret")
    text = client.get("/api/config").text
    assert "sk-super-secret" not in text and "jwt-super-secret" not in text


# ---------------- logging must not leak user data or secrets ----------------
class _Generator:
    def generate(self, question, context):
        return "Employees get twenty vacation days. [Source 1]"


def test_chat_logs_do_not_contain_the_question_or_answer(client, caplog, monkeypatch):
    monkeypatch.setattr(deps, "get_generator", lambda: _Generator())
    monkeypatch.setattr(get_settings(), "retrieval_threshold", 0.25)
    pdf = make_pdf([("HR Policy", VACATION)])
    client.post("/api/documents/upload", files={"file": ("hr.pdf", pdf, "application/pdf")})
    caplog.set_level(logging.DEBUG)
    secret_question = "How many vacation days do employees get? ticket9917unique"
    assert client.post("/api/chat", json={"question": secret_question}).status_code == 200
    assert "ticket9917unique" not in caplog.text
    assert "twenty vacation days" not in caplog.text            # answer text is not logged either


def test_api_key_never_appears_in_logs_when_the_llm_call_fails(caplog):
    caplog.set_level(logging.DEBUG)
    transport = httpx.MockTransport(lambda request: httpx.Response(401, json={"error": "bad key"}))
    client = OpenAICompatibleClient("https://api.example.com/v1", "m", api_key="sk-test-secret-123", transport=transport)
    with pytest.raises(LLMError):
        client.complete([{"role": "user", "content": "hi"}])
    assert "sk-test-secret-123" not in caplog.text
