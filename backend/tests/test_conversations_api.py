def test_conversation_lifecycle(client):
    r = client.post("/api/conversations", json={"title": "Q&A"})
    assert r.status_code == 201
    cid = r.json()["id"]

    assert len(client.get("/api/conversations").json()) == 1
    detail = client.get(f"/api/conversations/{cid}").json()
    assert detail["title"] == "Q&A" and detail["messages"] == []

    assert client.delete(f"/api/conversations/{cid}").status_code == 204
    assert client.get(f"/api/conversations/{cid}").status_code == 404
