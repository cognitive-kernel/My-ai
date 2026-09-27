from my_ai.access_policy import permission_for_path, read_only_blocked, is_public_path, assert_mutation_allowed


def test_route_permissions_are_centralized():
    assert permission_for_path("/code/run", "POST") == ("code-execution", "execute")
    assert permission_for_path("/memory/search/hybrid", "GET") == ("memory", "read")
    assert permission_for_path("/unknown/write", "POST") is None


def test_read_only_blocks_mutations_but_not_auth():
    assert read_only_blocked(True, "POST", "/code/run") is True
    assert read_only_blocked(True, "GET", "/memory/search/hybrid") is False
    assert read_only_blocked(True, "POST", "/auth/login") is False


def test_public_paths():
    assert is_public_path("/login")
    assert is_public_path("/docs/index.html")
    assert not is_public_path("/admin/readiness")


def test_process_wide_mutation_guard(monkeypatch):
    monkeypatch.setenv("MYAI_READ_ONLY", "true")
    import pytest
    with pytest.raises(PermissionError, match="MYAI_READ_ONLY"):
        assert_mutation_allowed("test")
    monkeypatch.setenv("MYAI_READ_ONLY", "false")
    assert_mutation_allowed("test")


def test_every_non_public_http_route_has_central_policy_mapping():
    from my_ai.api import app
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set()) or set()
        if not path or is_public_path(path) or path.startswith("/static/"):
            continue
        for method in methods - {"HEAD", "OPTIONS"}:
            assert permission_for_path(path, method) is not None, (method, path)
