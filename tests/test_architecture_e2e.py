from fastapi.testclient import TestClient

from my_ai.api import app
from my_ai import auth, db


def test_public_route_inventory_and_startup_lifecycle(tmp_path, monkeypatch):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "architecture.db"))
    db.init_db()
    try:
        client = TestClient(app)
        assert client.get("/health").status_code == 200
        routes = {(method, route.path) for route in app.routes for method in getattr(route, "methods", set())}
        assert ("POST", "/chat") in routes
        assert ("POST", "/chat/stream") in routes
        assert ("GET", "/models/health") in routes
    finally:
        object.__setattr__(db.settings, "db_path", old)


def test_main_request_boundary_propagates_policy_and_request_id(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "architecture-auth.db"))
    db.init_db()
    try:
        client = TestClient(app)
        response = client.post("/tools/python", json={})
        assert response.status_code in {303, 401, 403, 422}
        assert response.headers.get("X-Request-ID")
        user = auth.create_account("owner", "a-secure-password")
        cookie = {"myai_session": auth.create_session(user["id"])}
        denied = client.post("/admin/users", json={"username":"x","password":"third-secure-password"}, cookies=cookie)
        assert denied.status_code in {403, 422}
        assert denied.headers.get("X-Request-ID")
    finally:
        object.__setattr__(db.settings, "db_path", old)
