from my_ai import auth, db
from my_ai.access_policy import permission_for_path, is_public_path


def test_sensitive_routes_have_explicit_capabilities():
    routes = [
        ("POST", "/self-update/apply"),
        ("POST", "/self-repair/apply"),
        ("POST", "/backup/import"),
        ("POST", "/tools/python"),
        ("POST", "/skills/revalidate"),
        ("POST", "/admin/users"),
    ]
    for method, path in routes:
        permission = permission_for_path(path, method)
        assert permission is not None
        assert permission[1] in {"write", "execute"}


def test_non_admin_tool_permission_is_deny_by_default(monkeypatch):
    user = {"id": 9001, "username": "user", "role": "user"}
    monkeypatch.setattr(auth, "fetch_all", lambda *args, **kwargs: [])
    assert auth.tool_allowed(user, "python", "execute") is False


def test_admin_tool_permission_is_allowed_without_row():
    user = {"id": 1, "username": "admin", "role": "admin"}
    assert auth.tool_allowed(user, "python", "execute") is True


def test_public_paths_are_explicit_not_wildcard():
    assert is_public_path("/health")
    assert is_public_path("/docs/example")
    assert not is_public_path("/admin/anything")
    assert not is_public_path("/tools/python")


def test_audit_event_records_hashes_without_raw_payload(monkeypatch):
    captured = []
    monkeypatch.setattr(auth, "execute", lambda *args: captured.append(args))
    user = {"id": 7, "username": "user", "role": "user"}
    secret = "super-secret-password"
    auth.audit_event(user, "python", "execute", "403", request_id="req-1", input_data=secret, error="denied")
    details = captured[0][1][5]
    assert secret not in details
    assert "sha256" in details
    assert "req-1" in details
