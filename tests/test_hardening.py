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
    assert client.get("/register", follow_redirects=False).status_code == 303
    login = client.get("/login")
    assert "href='/register'" not in login.text


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

def test_knowledge_triggers_survive_reinit_and_update(client_db):
    db.remember_knowledge("Python", "عنوان", "محتوا")
    db.init_db()
    row_id=db.execute("UPDATE knowledge SET title=? WHERE id=?", ("عنوان جدید", 1))
    assert row_id == 1
    db.execute("UPDATE knowledge SET verification_status=? WHERE id=?", ("verified", 1))
    assert db.fetch_all("SELECT title FROM knowledge_fts WHERE rowid=1")[0]["title"] == "عنوان جدید"


def test_login_rate_limit_blocks_correct_password_after_failures(client_db):
    client=client_db
    auth.create_account("owner","a-secure-password")
    for _ in range(5):
        response=client.post("/auth/login",json={"username":"owner","password":"wrong-password"})
        assert response.status_code in (401,429)
    response=client.post("/auth/login",json={"username":"owner","password":"a-secure-password"})
    assert response.status_code == 429


def test_learning_target_does_not_match_c_inside_words():
    from my_ai.curriculum import resolve_learning_target
    assert resolve_learning_target("learn cooking") == "cooking"
    assert resolve_learning_target("how do machines learn") == "how do machines learn"
    assert resolve_learning_target("learn C") == "C"
    assert resolve_learning_target("learn Python") == "Python"


def test_remote_executor_normalizes_run_url(monkeypatch):
    import my_ai.executor as executor
    calls=[]
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"output":"ok","error":"","timed_out":False,"return_code":0}
    def fake_post(url,**kwargs):
        calls.append(url)
        return Response()
    monkeypatch.setattr(executor.httpx,"post",fake_post)
    monkeypatch.setenv("EXECUTOR_SHARED_TOKEN","real-test-token")
    monkeypatch.setenv("EXECUTOR_SERVICE_URL","http://executor:9000")
    executor._run_remote("print(1)")
    assert calls == ["http://executor:9000/run"]
