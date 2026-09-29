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


def test_chat_api_has_no_legacy_keyword_command_policy():
    from pathlib import Path
    source = Path("my_ai/api.py").read_text(encoding="utf-8")
    assert "parse_command" not in source
    assert "BUILD_WORDS" not in source

def test_knowledge_triggers_survive_reinit_and_update(client_db):
    knowledge_id = db.remember_knowledge("Python", "عنوان", "محتوا")
    db.init_db()
    db.execute("UPDATE knowledge SET title=? WHERE id=?", ("عنوان جدید", knowledge_id))
    assert db.fetch_all("SELECT title FROM knowledge WHERE id=?", (knowledge_id,))[0]["title"] == "عنوان جدید"
    db.execute("UPDATE knowledge SET verification_status=? WHERE id=?", ("verified", knowledge_id))
    assert db.fetch_all("SELECT title FROM knowledge_fts WHERE rowid=?", (knowledge_id,))[0]["title"] == "عنوان جدید"


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



def test_encrypted_backup_roundtrip_and_wrong_password():
    from my_ai.backup_crypto import decrypt_bytes, encrypt_bytes
    blob = encrypt_bytes(b"my-ai-backup", "a-strong-password")
    assert decrypt_bytes(blob, "a-strong-password") == b"my-ai-backup"
    with pytest.raises(Exception):
        decrypt_bytes(blob, "wrong-password")


def test_inference_metrics_record():
    from my_ai.metrics import record_inference, snapshot
    before = snapshot()["inference"].get("ollama:test-model", {}).get("requests", 0)
    record_inference("ollama", "test-model", 0.25, prompt_tokens=10, output_tokens=5)
    after = snapshot()["inference"]["ollama:test-model"]
    assert after["requests"] == before + 1
    assert after["prompt_tokens"] >= 10
    assert after["output_tokens"] >= 5


def test_repair_invalid_diff_retries(monkeypatch, tmp_path):
    from my_ai import self_repair
    monkeypatch.setattr(self_repair, "diagnose_local", lambda: {"head": "abc", "clean": True, "tests_passed": True, "tests": "ok", "lessons": []})
    monkeypatch.setattr(self_repair, "_test_patch", lambda patch, base: (True, "ok"))
    monkeypatch.setattr(self_repair, "PROPOSALS", tmp_path)
    class FakeLLM:
        def __init__(self): self.calls = 0
        def chat(self, prompt, system=None):
            self.calls += 1
            if self.calls < 3: return "not a patch"
            return "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1 @@\n-old\n+new\n"
    fake = FakeLLM()
    monkeypatch.setattr(self_repair, "create_llm", lambda task: fake)
    monkeypatch.setattr(self_repair, "execute", lambda *a, **k: None)
    result = self_repair.propose_repair("bad output")
    assert fake.calls == 3
    assert result["isolated_tests_passed"] is True


def test_offline_strict_blocks_public_web(monkeypatch):
    from my_ai import platform
    object.__setattr__(platform.settings, "offline_strict", True)
    result = platform.web_fetch_policy("https://example.com")
    assert result["allowed"] is False
    assert "offline strict" in result["reason"]


def test_health_metrics_is_public(client_db):
    client = client_db
    response = client.get("/health/metrics")
    assert response.status_code == 200
    assert "inference" in response.json()


def test_sqlite_tool_rejects_external_path(tmp_path):
    from my_ai import tooling
    with pytest.raises(ValueError):
        tooling.sqlite_schema(str(tmp_path / "other.db"))


def test_backup_path_rejects_external_path(tmp_path):
    from my_ai import platform
    with pytest.raises(ValueError):
        platform._safe_backup_path(str(tmp_path / "other.json"))


def test_backup_import_rejects_newer_format(tmp_path):
    from my_ai import platform
    import json
    path = tmp_path / "future.json"
    path.write_text(json.dumps({"metadata": {"format_version": 999}, "tables": {}}), encoding="utf-8")
    with pytest.raises(ValueError):
        platform.import_database(str(path))


def test_code_execution_requires_explicit_confirmation(client_db, monkeypatch):
    client = client_db
    owner = auth.create_account("owner", "a-secure-password")
    monkeypatch.setattr("my_ai.api.learner.validate_code", lambda code: {"ok": True})
    response = client.post("/code/run", json={"code": "print(1)"}, cookies=login_cookie(owner))
    assert response.status_code == 409
    response = client.post("/code/run", json={"code": "print(1)", "confirmed": True}, cookies=login_cookie(owner))
    assert response.status_code == 200

def test_general_chat_does_not_execute_learning_or_image_actions(client_db, monkeypatch):
    client = client_db
    owner = auth.create_account("owner", "a-secure-password")
    cookies = login_cookie(owner)
    from my_ai.domain.router import Intent
    monkeypatch.setattr("my_ai.api.classify", lambda message, context=None: Intent("learning", 0.99, False, {"language": "Python"}, ("learning",)))
    response = client.post("/chat", json={"message": "یاد بگیر Python"}, cookies=cookies)
    assert response.status_code == 409
    monkeypatch.setattr("my_ai.api.classify", lambda message, context=None: Intent("image_generation", 0.99, False, {}, ("image_generation",)))
    response = client.post("/chat", json={"message": "یک تصویر بساز"}, cookies=cookies)
    assert response.status_code == 409


def test_learning_command_endpoint_accepts_only_learning(client_db, monkeypatch):
    client = client_db
    owner = auth.create_account("owner", "a-secure-password")
    from my_ai.domain.router import Intent
    monkeypatch.setattr("my_ai.api.classify", lambda message: Intent("chat", 0.99, False, {}, ("chat",)))
    response = client.post("/learning/command", json={"message": "سلام"}, cookies=login_cookie(owner))
    assert response.status_code == 400

