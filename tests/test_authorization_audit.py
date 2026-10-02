from my_ai import auth, db
from my_ai.access_policy import permission_for_path


def test_sensitive_routes_have_explicit_capabilities():
    for path, method in (
        ("/self-update/apply", "POST"),
        ("/self-repair/apply", "POST"),
        ("/backup/import", "POST"),
        ("/tools/python", "POST"),
        ("/skills/revalidate", "POST"),
    ):
        permission = permission_for_path(path, method)
        assert permission is not None
        assert permission[1] in {"write", "execute"}


def test_tool_permission_is_deny_by_default(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "auth.db"))
    db.init_db()
    auth.create_account("bootstrap", "a-secure-password")
    user = auth.create_account("policy-user", "another-secure-password")
    assert auth.tool_allowed(user, "python", "execute") is False
    db.execute(
        "INSERT INTO tool_permissions(user_id,tool_name,action,allowed) VALUES(?,?,?,1)",
        (user["id"], "python", "execute"),
    )
    assert auth.tool_allowed(user, "python", "execute") is True
    object.__setattr__(db.settings, "db_path", old)


def test_audit_event_stores_hashes_not_raw_payload(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "audit.db"))
    db.init_db()
    user = auth.create_account("audit-user", "a-secure-password")
    secret = "do-not-store-this-secret"
    auth.audit_event(user, "python", "execute", "failure", request_id="req-1", input_data=secret, error="failed")
    row = db.fetch_all("SELECT details FROM audit_log ORDER BY id DESC LIMIT 1")[0]
    assert secret not in row["details"]
    assert "request_id" in row["details"]
    assert "sha256" in row["details"]
    object.__setattr__(db.settings, "db_path", old)


def test_configuration_registry_mutations_require_admin():
    from my_ai import settings_feature as sf
    routes = {(route.path, method) for route in sf.router.routes for method in getattr(route, "methods", set())}
    assert ("/settings/registry/{key:path}", "PUT") in routes
    assert ("/settings/registry/{key:path}/reset", "POST") in routes
    assert ("/settings/registry/import", "POST") in routes