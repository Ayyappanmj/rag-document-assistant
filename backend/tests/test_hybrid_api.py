from tests.conftest import make_pdf

REVENUE = "Revenue growth was strong in fiscal year 2025. " * 20
VACATION = "Employees receive twenty vacation days under the company vacation policy. " * 20


def _upload(client, name="report.pdf"):
    pdf = make_pdf([("Finance", REVENUE), ("HR Policy", VACATION)])
    return client.post("/api/documents/upload", files={"file": (name, pdf, "application/pdf")}).json()["id"]


def test_hybrid_is_default_mode_and_exposes_both_scores(client):
    _upload(client)
    hits = client.post("/api/search", json={"query": "vacation policy"}).json()
    assert hits[0]["page_number"] == 2
    assert hits[0]["retrieval_type"] == "hybrid"
    assert hits[0]["dense_score"] is not None and hits[0]["bm25_score"] is not None
    assert 0.0 <= hits[0]["score"] <= 1.0


def test_hybrid_top_k_and_ordering(client):
    _upload(client)
    hits = client.post("/api/search", json={"query": "revenue growth", "top_k": 2, "mode": "hybrid"}).json()
    assert len(hits) == 2
    assert hits[0]["score"] >= hits[1]["score"]
    assert hits[0]["page_number"] == 1


def test_hybrid_multi_document_filter(client):
    first, second = _upload(client, "a.pdf"), _upload(client, "b.pdf")
    both = client.post("/api/search", json={"query": "revenue", "top_k": 10}).json()
    assert {h["document_id"] for h in both} == {first, second}
    only = client.post("/api/search", json={"query": "revenue", "document_ids": [second]}).json()
    assert only and all(h["document_id"] == second for h in only)


def test_hybrid_no_documents(client):
    assert client.post("/api/search", json={"query": "anything"}).json() == []
