PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def _upload(client, name="report.pdf", data=PDF_BYTES):
    return client.post("/api/documents/upload", files={"file": (name, data, "application/pdf")})


def test_upload_valid_pdf(client):
    r = _upload(client)
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "report.pdf"
    assert body["status"] == "processing"


def test_upload_rejects_non_pdf_extension(client):
    assert _upload(client, name="notes.txt").status_code == 415


def test_upload_rejects_fake_pdf(client):
    assert _upload(client, data=b"not really a pdf").status_code == 415


def test_upload_rejects_empty(client):
    assert _upload(client, data=b"").status_code in (400, 415)


def test_upload_rejects_too_large(client, monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)
    assert _upload(client).status_code == 413


def test_list_get_delete(client):
    doc_id = _upload(client).json()["id"]
    assert len(client.get("/api/documents").json()) == 1
    assert client.get(f"/api/documents/{doc_id}").status_code == 200
    assert client.delete(f"/api/documents/{doc_id}").status_code == 204
    assert client.get(f"/api/documents/{doc_id}").status_code == 404


def test_get_missing_document(client):
    assert client.get("/api/documents/nope").status_code == 404
