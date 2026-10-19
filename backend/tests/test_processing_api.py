from tests.conftest import make_pdf

BODY = "Revenue increased by 18 percent in fiscal year 2025. " * 30


def test_real_pdf_is_processed_end_to_end(client):
    pdf = make_pdf([("Overview", BODY), ("Outlook", BODY)])
    r = client.post("/api/documents/upload", files={"file": ("report.pdf", pdf, "application/pdf")})
    assert r.status_code == 201
    doc_id = r.json()["id"]

    doc = client.get(f"/api/documents/{doc_id}").json()  # background task already finished
    assert doc["status"] == "ready"
    assert doc["page_count"] == 2
    assert doc["chunk_count"] > 0

    chunks = client.get(f"/api/documents/{doc_id}/chunks").json()
    assert len(chunks) == doc["chunk_count"]
    assert chunks[0]["page_number"] == 1
    page2 = client.get(f"/api/documents/{doc_id}/chunks", params={"page": 2}).json()
    assert page2 and all(c["page_number"] == 2 for c in page2)


def test_unreadable_pdf_is_marked_failed(client):
    fake = b"%PDF-1.4\nthis is not a real pdf body"
    doc_id = client.post(
        "/api/documents/upload", files={"file": ("bad.pdf", fake, "application/pdf")}
    ).json()["id"]
    doc = client.get(f"/api/documents/{doc_id}").json()
    assert doc["status"] == "failed"
    assert doc["error_message"]


def test_chunks_of_missing_document_404(client):
    assert client.get("/api/documents/nope/chunks").status_code == 404
