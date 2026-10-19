from tests.conftest import make_pdf

REVENUE = "Revenue growth was strong in fiscal year 2025. " * 20
VACATION = "Employees receive twenty vacation days under the company vacation policy. " * 20


def _upload(client, name="report.pdf"):
    pdf = make_pdf([("Finance", REVENUE), ("HR Policy", VACATION)])
    return client.post("/api/documents/upload", files={"file": (name, pdf, "application/pdf")}).json()["id"]


def _search(client, query, mode="bm25", **extra):
    return client.post("/api/search", json={"query": query, "mode": mode, **extra})


def test_bm25_search_finds_keyword(client):
    _upload(client)
    hits = _search(client, "vacation").json()
    assert hits[0]["page_number"] == 2
    assert hits[0]["retrieval_type"] == "bm25"


def test_bm25_unknown_word_returns_empty(client):
    _upload(client)
    assert _search(client, "zeppelin").json() == []


def test_bm25_respects_document_filter(client):
    _upload(client, "a.pdf")
    second = _upload(client, "b.pdf")
    hits = _search(client, "revenue", document_ids=[second]).json()
    assert hits and all(h["document_id"] == second for h in hits)


def test_bm25_after_delete_returns_nothing(client):
    doc_id = _upload(client)
    assert _search(client, "vacation").json()
    client.delete(f"/api/documents/{doc_id}")
    assert _search(client, "vacation").json() == []


def test_invalid_mode_rejected(client):
    assert _search(client, "x", mode="magic").status_code == 422
