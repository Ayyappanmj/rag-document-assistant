import json

from app.config import get_settings


def test_comparison_endpoint_404_until_a_benchmark_exists(client, tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "evaluation_dir", str(tmp_path / "empty"))
    assert client.get("/api/evaluation/vector-stores").status_code == 404


def test_comparison_endpoint_returns_the_saved_benchmark(client, tmp_path, monkeypatch):
    (tmp_path / "eval").mkdir()
    saved = {
        "label": "Vector store benchmark", "note": "n", "generated_at": "2026-01-01T00:00:00+00:00",
        "environment": {"python": "3.11"}, "parameters": {"vectors": 100},
        "stores": {"faiss": {"index_type": "Flat (exact search)", "recall_at_k": 1.0}},
    }
    (tmp_path / "eval" / "vector_store_comparison.json").write_text(json.dumps(saved), encoding="utf-8")
    monkeypatch.setattr(get_settings(), "evaluation_dir", str(tmp_path / "eval"))
    body = client.get("/api/evaluation/vector-stores").json()
    assert body["stores"]["faiss"]["recall_at_k"] == 1.0 and body["real_documents"] is None


def test_corrupt_comparison_file_is_treated_as_missing(client, tmp_path, monkeypatch):
    (tmp_path / "eval").mkdir()
    (tmp_path / "eval" / "vector_store_comparison.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(get_settings(), "evaluation_dir", str(tmp_path / "eval"))
    assert client.get("/api/evaluation/vector-stores").status_code == 404


def test_config_endpoint_reports_the_active_vector_store(client):
    assert client.get("/api/config").json()["vector_store"] in ("faiss", "chroma")
