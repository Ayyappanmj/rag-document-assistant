import pytest

from app.config import get_settings
from app.rag import dependencies as deps
from tests.conftest import make_pdf

REVENUE = "Revenue growth was strong in fiscal year 2025. " * 20
VACATION = "Employees receive twenty vacation days under the company vacation policy. " * 20


class FakeGenerator:
    def generate(self, question, context):
        return "Employees get twenty vacation days. [Source 1]"


@pytest.fixture
def gen(monkeypatch):
    monkeypatch.setattr(get_settings(), "retrieval_threshold", 0.35)
    monkeypatch.setattr(deps, "get_generator", lambda: FakeGenerator())


def test_empty_dashboard(client):
    body = client.get("/api/dashboard/stats").json()
    assert body["total_documents"] == 0 and body["questions_asked"] == 0
    assert body["avg_response_time_ms"] is None
    assert body["recent_documents"] == [] and body["recent_questions"] == []
    assert body["evaluation"]["evaluated_answers"] == 0 and body["evaluation"]["faithfulness"] is None


def test_dashboard_reflects_uploads_and_chat(client, gen):
    pdf = make_pdf([("Finance", REVENUE), ("HR Policy", VACATION)])
    client.post("/api/documents/upload", files={"file": ("report.pdf", pdf, "application/pdf")})
    client.post("/api/chat", json={"question": "How many vacation days do employees get?"})

    body = client.get("/api/dashboard/stats").json()
    assert body["total_documents"] == 1 and body["total_pages"] == 2 and body["total_chunks"] > 0
    assert body["questions_asked"] == 1 and body["grounded_answers"] == 1 and body["ungrounded_answers"] == 0
    assert body["avg_response_time_ms"] > 0
    assert body["recent_documents"][0]["name"] == "report.pdf"
    assert body["recent_questions"][0]["question"].startswith("How many vacation")
    assert body["evaluation"]["evaluated_answers"] == 1 and body["evaluation"]["faithfulness"] == 1.0


def test_config_endpoint_has_no_secrets(client):
    r = client.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    assert {"llm_provider", "top_k", "max_upload_mb", "embedding_model"} <= set(body)
    text = r.text.lower()
    assert "secret" not in text and "api_key" not in text
