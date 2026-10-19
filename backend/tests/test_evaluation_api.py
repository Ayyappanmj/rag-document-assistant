import json
import threading
import time

import pytest

from app.config import get_settings
from app.rag import dependencies as deps
from app.services.evaluation_jobs import EvaluationJobManager, job_manager
from tests.conftest import make_pdf

REVENUE = "Revenue growth was strong in fiscal year 2025. " * 20
VACATION = "Employees receive twenty vacation days under the company vacation policy. " * 20

QUESTIONS = [
    {"id": "t1", "type": "factual", "question": "How many vacation days do employees get?",
     "ground_truth": "Employees receive twenty vacation days.", "expected_sources": ["report.pdf"], "answerable": True},
    {"id": "t2", "type": "unanswerable", "question": "zeppelin quantum",
     "ground_truth": "Not in the documents.", "expected_sources": [], "answerable": False},
]


class FakeGenerator:
    def generate(self, question, context):
        return "Employees get twenty vacation days. [Source 1]"


@pytest.fixture
def env(client, tmp_path, monkeypatch):
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    (eval_dir / "questions.json").write_text(json.dumps(QUESTIONS), encoding="utf-8")
    settings = get_settings()
    monkeypatch.setattr(settings, "evaluation_dir", str(eval_dir))
    monkeypatch.setattr(settings, "retrieval_threshold", 0.35)
    monkeypatch.setattr(deps, "get_generator", lambda: FakeGenerator())
    job_manager.reset()
    yield eval_dir
    job_manager.reset()


def _upload(client):
    pdf = make_pdf([("Finance", REVENUE), ("HR Policy", VACATION)])
    client.post("/api/documents/upload", files={"file": ("report.pdf", pdf, "application/pdf")})


def _wait(client):
    for _ in range(200):
        status = client.get("/api/evaluation/status").json()
        if status["state"] in ("completed", "failed"):
            return status
        time.sleep(0.05)
    raise AssertionError("evaluation did not finish")


def test_metrics_before_any_run(client, env):
    body = client.get("/api/evaluation/metrics").json()
    assert body["sample"] is None and body["live"]["questions_asked"] == 0
    assert client.get("/api/evaluation/results").status_code == 404


def test_start_requires_sample_documents(client, env):
    r = client.post("/api/evaluate")
    assert r.status_code == 409 and "report.pdf" in r.json()["detail"]


def test_missing_dataset_returns_404(client, env):
    (env / "questions.json").unlink()
    assert client.post("/api/evaluate").status_code == 404


def test_full_run_produces_summary_results_and_file(client, env):
    _upload(client)
    r = client.post("/api/evaluate")
    assert r.status_code == 202 and r.json()["state"] == "running"
    status = _wait(client)
    assert status["state"] == "completed" and status["completed"] == 2

    metrics = client.get("/api/evaluation/metrics").json()
    sample, summary = metrics["sample"], metrics["sample"]["summary"]
    assert sample["label"] == "Sample Evaluation" and "not a scientific benchmark" in sample["note"]
    assert summary["total_questions"] == 2 and summary["answerable_questions"] == 1
    assert summary["refusal_accuracy"] == 1.0 and summary["false_refusal_rate"] == 0.0
    assert summary["retrieval_recall"] == 1.0 and summary["faithfulness"] == 1.0
    assert summary["answer_match"] >= 0.7
    assert summary["grounded_answers"] == 1

    rows = client.get("/api/evaluation/results").json()["results"]
    assert [row["id"] for row in rows] == ["t1", "t2"]
    assert rows[0]["retrieved_context"] and rows[0]["expected_answer"] and rows[0]["generated_answer"]
    assert rows[1]["refused"] is True and rows[1]["answer_match"] is None

    saved = json.loads((env / "results.json").read_text(encoding="utf-8"))
    assert saved["label"] == "Sample Evaluation" and len(saved["results"]) == 2

    # dataset runs must not pollute the live-usage numbers
    assert metrics["live"]["evaluated_answers"] == 0


def test_limit_runs_only_first_questions(client, env):
    _upload(client)
    client.post("/api/evaluate", json={"limit": 1})
    assert _wait(client)["total"] == 1
    assert client.get("/api/evaluation/metrics").json()["sample"]["summary"]["total_questions"] == 1


def test_live_metrics_reflect_chat_usage(client, env):
    _upload(client)
    client.post("/api/chat", json={"question": "How many vacation days do employees get?"})
    live = client.get("/api/evaluation/metrics").json()["live"]
    assert live["questions_asked"] == 1 and live["evaluated_answers"] == 1
    assert live["grounded_answers"] == 1 and live["faithfulness"] == 1.0
    assert live["avg_retrieval_score"] > 0 and live["avg_response_time_ms"] > 0


def test_job_manager_rejects_second_run_while_running():
    manager, release = EvaluationJobManager(), threading.Event()
    assert manager.start(lambda progress: release.wait(5), total=3) is True
    assert manager.status()["state"] == "running"
    assert manager.start(lambda progress: None, total=1) is False
    release.set()
    for _ in range(100):
        if manager.status()["state"] == "completed":
            break
        time.sleep(0.02)
    assert manager.status()["state"] == "completed"


def test_job_manager_reports_failure_safely():
    manager = EvaluationJobManager()

    def boom(progress):
        raise RuntimeError("secret internal detail")

    manager.start(boom, total=1)
    for _ in range(100):
        if manager.status()["state"] == "failed":
            break
        time.sleep(0.02)
    status = manager.status()
    assert status["state"] == "failed" and "secret" not in status["error"]
