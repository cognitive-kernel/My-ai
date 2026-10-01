from fastapi.testclient import TestClient
from my_ai import auth, db
from my_ai.api import app


def _login(user):
    return {"myai_session": auth.create_session(user["id"])}


def test_session_lifecycle_and_isolation(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "session.db"))
    db.init_db()
    try:
        client = TestClient(app)
        owner = auth.create_account("owner", "a-secure-password")
        sid = client.post("/chat/sessions", json={"message": "first"}, cookies=_login(owner)).json()["id"]
        assert client.get("/chat/sessions", cookies=_login(owner)).status_code == 200
        assert client.patch(f"/chat/sessions/{sid}", json={"message": "renamed"}, cookies=_login(owner)).status_code == 200
        assert client.post(f"/chat/sessions/{sid}/pin", cookies=_login(owner)).status_code == 200
        assert client.get(f"/chat/history?session_id={sid}", cookies=_login(owner)).status_code == 200
        assert client.delete(f"/chat/sessions/{sid}", cookies=_login(owner)).status_code == 200
        assert client.get(f"/chat/history?session_id={sid}", cookies=_login(owner)).status_code == 404
    finally:
        object.__setattr__(db.settings, "db_path", old)


def test_stream_requires_owned_session(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "stream.db"))
    db.init_db()
    try:
        client = TestClient(app)
        owner = auth.create_account("owner", "a-secure-password")
        member = auth.create_account("member", "another-secure-password")
        sid = client.post("/chat/sessions", json={"message": "owned"}, cookies=_login(owner)).json()["id"]
        response = client.post("/chat/stream", json={"message": "x", "session_id": sid}, cookies=_login(member))
        assert response.status_code == 404
    finally:
        object.__setattr__(db.settings, "db_path", old)
