import pytest
from fastapi.testclient import TestClient

from my_ai import auth, db
from my_ai.access_policy import permission_for_path, is_mutation
from my_ai.api import app


SENSITIVE = [
    ("POST", "/self-update/apply"), ("POST", "/self-repair/apply"),
    ("POST", "/backup/import"), ("POST", "/tools/python"),
    ("POST", "/skills/revalidate"), ("POST", "/admin/users"),
]


def _cookie(user):
    return {"myai_session": auth.create_session(user["id"])}


def test_sensitive_capabilities_have_explicit_policy():
    for method, path in SENSITIVE:
        permission = permission_for_path(path, method)
        assert permission is not None
        assert permission[1] in {"write", "execute"}


def test_mutation_boundary_is_explicit():
    assert all(is_mutation(m) for m in ("POST", "PUT", "PATCH", "DELETE"))
    assert not is_mutation("GET")


def test_non_admin_cannot_use_admin_mutations(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "auth.db")); db.init_db()
    try:
        client = TestClient(app)
        admin = auth.create_account("admin", "a-secure-password")
        member = auth.create_account("member", "another-secure-password")
        response = client.post("/admin/users", json={"username": "x", "password": "third-secure-password"}, cookies=_cookie(member))
        assert response.status_code in {401, 403}
        assert admin["role"] == "admin"
    finally:
        object.__setattr__(db.settings, "db_path", old)


def test_direct_sensitive_route_requires_authenticated_actor(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "auth2.db")); db.init_db()
    try:
        client = TestClient(app, follow_redirects=False)
        for method, path in SENSITIVE:
            response = client.request(method, path, json={})
            assert response.status_code in {401, 403, 409, 422, 303}, (method, path, response.status_code)
    finally:
        object.__setattr__(db.settings, "db_path", old)
