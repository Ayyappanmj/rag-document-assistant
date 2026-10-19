import pytest

from app.config import get_settings
from app.rag import dependencies as deps
from app.models.database import Evaluation
from app.models.database import get_session_factory
from app.rag.generator import LLMError
from app.rag.prompt import INSUFFICIENT_EVIDENCE, NO_ANSWER
from tests.conftest import make_pdf

REVENUE = "Revenue growth was strong in fiscal year 2025. " * 20
VACATION = "Employees receive twenty vacation days under the company vacation policy. " * 20


class FakeGenerator:
    def __init__(self, answer="Employees get twenty vacation days. [Source 1]", error=None):
        self.answer, self.error, self.calls = answer, error, []

    def generate(self, question, context):
        self.calls.append((question, context))
        if self.error:
            raise self.error
        return self.answer


@pytest.fixture
def gen(monkeypatch):
    monkeypatch.setattr(get_settings(), "retrieval_threshold", 0.35)
    generator = FakeGenerator()
    monkeypatch.setattr(deps, "get_generator", lambda: generator)
    return generator


def _upload(client, name="report.pdf"):
    pdf = make_pdf([("Finance", REVENUE), ("HR Policy", VACATION)])
    return client.post("/api/documents/upload", files={"file": (name, pdf, "application/pdf")}).json()["id"]


def _chat(client, question="How many vacation days do employees get?", **extra):
    return client.post("/api/chat", json={"question": question, **extra})


def test_chat_returns_answer_citations_and_metrics(client, gen):
    _upload(client)
    r = _chat(client)
    assert r.status_code == 200
    body = r.json()
    assert body["answer"].startswith("Employees get twenty")
    top = body["citations"][0]
    assert top["document"] == "report.pdf" and top["page"] == 2
    assert top["retrieval_type"] == "hybrid" and 0 < top["score"] <= 1
    m = body["metrics"]
    assert m["total_time_ms"] >= m["retrieval_time_ms"] >= 0


def test_context_sent_to_llm_is_numbered_and_sourced(client, gen):
    _upload(client)
    _chat(client)
    question, context = gen.calls[0]
    assert "vacation" in question
    assert "[Source 1] report.pdf, Page 2" in context


def test_messages_and_citations_are_persisted(client, gen):
    _upload(client)
    body = _chat(client).json()
    detail = client.get(f"/api/conversations/{body['conversation_id']}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["citations"][0]["document"] == "report.pdf"
    assert detail["messages"][1]["metrics"]["total_time_ms"] > 0
    assert detail["title"].startswith("How many vacation")


def test_follow_up_uses_same_conversation(client, gen):
    _upload(client)
    cid = _chat(client).json()["conversation_id"]
    again = _chat(client, "And what about revenue growth?", conversation_id=cid).json()
    assert again["conversation_id"] == cid
    assert len(client.get(f"/api/conversations/{cid}").json()["messages"]) == 4


def test_below_threshold_skips_llm(client, gen):
    _upload(client)
    body = _chat(client, "zeppelin quantum").json()
    assert body["answer"] == INSUFFICIENT_EVIDENCE
    assert body["citations"] == []
    assert gen.calls == []
    assert body["metrics"]["generation_time_ms"] == 0


def test_no_documents_returns_insufficient_evidence(client, gen):
    assert _chat(client).json()["answer"] == INSUFFICIENT_EVIDENCE
    assert gen.calls == []


def test_model_refusal_returns_no_citations(client, gen):
    gen.answer = NO_ANSWER
    _upload(client)
    body = _chat(client).json()
    assert body["answer"] == NO_ANSWER and body["citations"] == []


def test_document_filter_limits_citations(client, gen):
    _upload(client, "a.pdf")
    second = _upload(client, "b.pdf")
    body = _chat(client, document_ids=[second]).json()
    assert body["citations"] and {c["document_id"] for c in body["citations"]} == {second}


def test_llm_failure_returns_503_and_saves_nothing(client, gen):
    gen.error = LLMError("Could not reach the language model server.")
    _upload(client)
    r = _chat(client)
    assert r.status_code == 503
    assert "language model" in r.json()["detail"]
    assert client.get("/api/conversations").json() == []


def test_validation_and_unknown_conversation(client, gen):
    assert client.post("/api/chat", json={"question": ""}).status_code == 422
    assert _chat(client, conversation_id="nope").status_code == 404


def test_inline_markers_rewritten_to_readable_form(client, gen):
    _upload(client)
    answer = _chat(client).json()["answer"]
    assert "[Source: report.pdf, Page 2]" in answer
    assert "[Source 1]" not in answer


def test_only_cited_sources_are_returned(client, gen):
    gen.answer = "Employees get twenty vacation days. [Source 1]"
    _upload(client)
    body = _chat(client, top_k=5).json()
    assert len(body["citations"]) == 1
    assert body["citation_coverage"] == 1.0


def test_uncited_answer_falls_back_to_retrieved_sources(client, gen):
    gen.answer = "Employees receive twenty vacation days per year."
    _upload(client)
    body = _chat(client).json()
    assert body["citation_coverage"] == 0.0
    assert len(body["citations"]) > 1


def test_invented_source_numbers_are_reported_and_stripped(client, gen):
    gen.answer = "Employees receive twenty vacation days. [Source 99]"
    _upload(client)
    body = _chat(client).json()
    assert body["invalid_citations"] == [99]
    assert "99" not in body["answer"]


def test_citation_coverage_is_persisted(client, gen):
    _upload(client)
    cid = _chat(client).json()["conversation_id"]
    metrics = client.get(f"/api/conversations/{cid}").json()["messages"][1]["metrics"]
    assert metrics["citation_coverage"] == 1.0 and metrics["invalid_citations"] == []


HALLUCINATION = "The company opened a new office in Tokyo last year. [Source 1]"


def test_supported_answer_is_grounded_with_scores(client, gen):
    _upload(client)
    body = _chat(client).json()
    assert body["grounded"] is True
    assert body["confidence"] > 0.7 and body["faithfulness"] == 1.0
    assert 0 <= body["answer_relevance"] <= 1 and 0 <= body["context_relevance"] <= 1
    assert body["unsupported_claims"] == []
    assert body["metrics"]["evaluation_time_ms"] >= 0


def test_hallucinated_answer_is_flagged(client, gen):
    gen.answer = HALLUCINATION
    _upload(client)
    body = _chat(client).json()
    assert body["grounded"] is False
    assert body["unsupported_claims"]
    assert body["answer"].startswith("The company opened")  # shown, but flagged


def test_block_ungrounded_replaces_answer(client, gen, monkeypatch):
    monkeypatch.setattr(get_settings(), "block_ungrounded", True)
    gen.answer = HALLUCINATION
    _upload(client)
    body = _chat(client).json()
    assert body["answer"] == INSUFFICIENT_EVIDENCE and body["citations"] == []
    assert body["grounded"] is False


def test_grounding_saved_on_message_and_evaluation_row(client, gen):
    _upload(client)
    body = _chat(client).json()
    msg = client.get(f"/api/conversations/{body['conversation_id']}").json()["messages"][1]
    assert msg["grounded"] is True and msg["confidence"] == body["confidence"]
    assert msg["metrics"]["faithfulness"] == 1.0

    session_factory = client.app.dependency_overrides[get_session_factory]()
    with session_factory() as db:
        rows = db.query(Evaluation).all()
    assert len(rows) == 1
    assert rows[0].message_id == body["message_id"] and rows[0].faithfulness == 1.0
    assert rows[0].citation_coverage == 1.0 and rows[0].is_sample is False


def test_no_answer_means_no_grounding_and_no_evaluation_row(client, gen):
    body = _chat(client).json()  # no documents -> insufficient evidence
    assert body["grounded"] is None and body["confidence"] is None
    session_factory = client.app.dependency_overrides[get_session_factory]()
    with session_factory() as db:
        assert db.query(Evaluation).count() == 0


def test_invented_citation_makes_answer_not_grounded(client, gen):
    gen.answer = "Employees get twenty vacation days. [Source 99]"
    _upload(client)
    assert _chat(client).json()["grounded"] is False


def test_evaluator_failure_does_not_break_chat(client, gen, monkeypatch):
    class Broken:
        def evaluate(self, *a, **k):
            raise RuntimeError("boom")

    monkeypatch.setattr(deps, "get_grounding_evaluator", lambda: Broken())
    _upload(client)
    r = _chat(client)
    assert r.status_code == 200
    assert r.json()["grounded"] is None and r.json()["answer"]


def _db(client):
    return client.app.dependency_overrides[get_session_factory]()()


def test_regenerate_replaces_last_exchange(client, gen):
    from app.models.database import Citation

    _upload(client)
    cid = _chat(client).json()["conversation_id"]
    r = _chat(client, conversation_id=cid, regenerate=True)
    assert r.status_code == 200
    detail = client.get(f"/api/conversations/{cid}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    assert detail["messages"][1]["id"] == r.json()["message_id"]
    with _db(client) as db:
        assert db.query(Evaluation).count() == 1  # old evaluation row removed
        assert db.query(Citation).count() == len(r.json()["citations"])  # old citations removed


def test_regenerate_with_a_different_question_keeps_history(client, gen):
    _upload(client)
    cid = _chat(client).json()["conversation_id"]
    _chat(client, "A completely different question about revenue", conversation_id=cid, regenerate=True)
    assert len(client.get(f"/api/conversations/{cid}").json()["messages"]) == 4


def test_failed_regenerate_keeps_the_old_answer(client, gen):
    _upload(client)
    first = _chat(client).json()
    gen.error = LLMError("Could not reach the language model server.")
    assert _chat(client, conversation_id=first["conversation_id"], regenerate=True).status_code == 503
    messages = client.get(f"/api/conversations/{first['conversation_id']}").json()["messages"]
    assert len(messages) == 2 and messages[1]["id"] == first["message_id"]
