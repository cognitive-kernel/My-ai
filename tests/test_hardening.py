import pytest
from fastapi.testclient import TestClient

from my_ai import auth, db
from my_ai.api import app


@pytest.fixture()
def client_db(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "api.db"))
    db.init_db()
    try:
        yield TestClient(app)
    finally:
        object.__setattr__(db.settings, "db_path", old)


def login_cookie(user):
    return {"myai_session": auth.create_session(user["id"])}


def test_registration_closes_and_login_link_disappears(client_db):
    client = client_db
    response = client.get("/auth/register/status")
    assert response.json()["open"] is True
    first = client.post("/auth/register", json={"username": "owner", "password": "a-secure-password"})
    assert first.status_code == 200
    assert first.json()["user"]["role"] == "admin"
    assert client.get("/auth/register/status").json()["open"] is False
    assert client.get("/register").status_code == 303
    login = client.get("/login")
    assert "register-link" in login.text


def test_non_admin_chat_requires_chat_permission(client_db):
    client = client_db
    auth.create_account("owner", "a-secure-password")
    member = auth.create_account("member", "another-secure-password")
    response = client.post("/chat", json={"message": "hello"}, cookies=login_cookie(member))
    assert response.status_code == 403


def test_chat_session_isolation(client_db):
    client = client_db
    owner = auth.create_account("owner", "a-secure-password")
    member = auth.create_account("member", "another-secure-password")
    db.execute("INSERT INTO tool_permissions(user_id,tool_name,action,allowed) VALUES(?,?,?,1)", (member["id"], "chat", "read"))
    owner_sid = client.post("/chat/sessions", json={"message": "owner"}, cookies=login_cookie(owner)).json()["id"]
    response = client.get(f"/chat/history?session_id={owner_sid}", cookies=login_cookie(member))
    assert response.status_code == 200
    assert response.json()["messages"] == []


def test_curly_apostrophe_does_not_request_fix():
    from my_ai.command_policy import parse_command
    policy = parse_command("don't fix this")
    assert policy.security_action != "fix"
    policy = parse_command("don’t fix this")
    assert policy.security_action != "fix"
