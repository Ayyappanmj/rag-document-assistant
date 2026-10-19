import pytest
from fastapi.testclient import TestClient

from app.models.database import Document, User


def test_register_and_login_flow(client: TestClient):
    # 1. Register
    reg_resp = client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "securepassword123"},
    )
    assert reg_resp.status_code == 201
    data = reg_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@example.com"
    token = data["access_token"]

    # 2. Duplicate registration fails
    dup_resp = client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "password": "anotherpassword"},
    )
    assert dup_resp.status_code == 400

    # 3. Login with wrong password fails
    bad_login = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "wrongpassword"},
    )
    assert bad_login.status_code == 401

    # 4. Login with correct password succeeds
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "securepassword123"},
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

    # 5. Access /api/auth/me with bearer token
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "alice@example.com"


def test_per_user_document_scoping(client: TestClient):
    # Register User 1 (Alice)
    r1 = client.post(
        "/api/auth/register",
        json={"email": "user1@example.com", "password": "password123"},
    )
    t1 = r1.json()["access_token"]

    # Register User 2 (Bob)
    r2 = client.post(
        "/api/auth/register",
        json={"email": "user2@example.com", "password": "password123"},
    )
    t2 = r2.json()["access_token"]

    # Alice creates conversation
    conv_resp = client.post(
        "/api/conversations",
        json={"title": "Alice's Secret Chat"},
        headers={"Authorization": f"Bearer {t1}"},
    )
    assert conv_resp.status_code == 201
    conv_id = conv_resp.json()["id"]

    # Alice lists conversations - sees her conversation
    list1 = client.get("/api/conversations", headers={"Authorization": f"Bearer {t1}"})
    assert any(c["id"] == conv_id for c in list1.json())

    # Bob lists conversations - does NOT see Alice's conversation
    list2 = client.get("/api/conversations", headers={"Authorization": f"Bearer {t2}"})
    assert not any(c["id"] == conv_id for c in list2.json())

    # Bob cannot view Alice's conversation
    get_alice_conv = client.get(f"/api/conversations/{conv_id}", headers={"Authorization": f"Bearer {t2}"})
    assert get_alice_conv.status_code == 404
