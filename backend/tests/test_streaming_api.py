import json
import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.rag import dependencies as deps
from tests.conftest import make_pdf

REVENUE = "Revenue growth was strong in fiscal year 2025. " * 20
VACATION = "Employees receive twenty vacation days under the company vacation policy. " * 20


class FakeStreamingGenerator:
    def __init__(self, answer="Employees get twenty vacation days. [Source 1]"):
        self.answer = answer

    def generate(self, question, context):
        return self.answer

    def generate_stream(self, question, context):
        tokens = self.answer.split(" ")
        for i, token in enumerate(tokens):
            yield token + (" " if i < len(tokens) - 1 else "")


@pytest.fixture
def stream_gen(monkeypatch):
    monkeypatch.setattr(get_settings(), "retrieval_threshold", 0.35)
    generator = FakeStreamingGenerator()
    monkeypatch.setattr(deps, "get_generator", lambda: generator)
    return generator


def test_chat_stream_returns_sse_events(client: TestClient, stream_gen):
    # Upload document
    pdf = make_pdf([("Finance", REVENUE), ("HR Policy", VACATION)])
    doc_id = client.post("/api/documents/upload", files={"file": ("policy.pdf", pdf, "application/pdf")}).json()["id"]

    # Request streaming answer
    res = client.post("/api/chat/stream", json={"question": "How many vacation days do employees get?"})
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    lines = res.text.strip().split("\n\n")
    events = []
    for line in lines:
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))

    event_types = [e["type"] for e in events]
    assert "sources" in event_types
    assert "token" in event_types
    assert "done" in event_types

    # Reconstruct streamed tokens
    tokens = [e["token"] for e in events if e["type"] == "token"]
    streamed_text = "".join(tokens)
    assert "Employees get twenty vacation days" in streamed_text

    # Verify done event contains full ChatResponse
    done_event = next(e for e in events if e["type"] == "done")
    resp_data = done_event["response"]
    assert resp_data["conversation_id"] is not None
    assert len(resp_data["citations"]) > 0
    assert resp_data["citations"][0]["document"] == "policy.pdf"
