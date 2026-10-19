from tests.conftest import make_pdf

REVENUE = "Revenue growth was strong in fiscal year 2025. " * 20
VACATION = "Employees receive twenty vacation days under the company vacation policy. " * 20


def _upload(client, name="report.pdf"):
    pdf = make_pdf([("Finance", REVENUE), ("HR Policy", VACATION)])
    r = client.post("/api/documents/upload", files={"file": (name, pdf, "application/pdf")})
    assert r.status_code == 201
    return r.json()["id"]


def test_upload_embeds_and_indexes(client, vector_store):
    doc_id = _upload(client)
    doc = client.get(f"/api/documents/{doc_id}").json()
    assert doc["status"] == "ready"
    assert vector_store.count == doc["chunk_count"] > 0


def test_search_endpoint_finds_right_page(client):
    _upload(client)
    hits = client.post("/api/search", json={"query": "vacation policy", "top_k": 3, "mode": "dense"}).json()
    assert hits[0]["page_number"] == 2
    assert hits[0]["retrieval_type"] == "dense"
    assert hits[0]["document_name"] == "report.pdf"


def test_search_with_no_documents_returns_empty(client):
    assert client.post("/api/search", json={"query": "anything"}).json() == []


def test_search_validates_input(client):
    assert client.post("/api/search", json={"query": ""}).status_code == 422


def test_search_filters_by_document(client):
    first, second = _upload(client, "a.pdf"), _upload(client, "b.pdf")
    hits = client.post("/api/search", json={"query": "revenue", "document_ids": [second]}).json()
    assert hits and all(h["document_id"] == second for h in hits)


def test_delete_document_removes_vectors(client, vector_store):
    doc_id = _upload(client)
    assert vector_store.count > 0
    assert client.delete(f"/api/documents/{doc_id}").status_code == 204
    assert vector_store.count == 0
