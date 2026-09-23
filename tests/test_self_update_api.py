from my_ai import api


def test_self_update_api_uses_real_module():
    assert api.self_update_status.__module__ == "my_ai.self_update"
    assert api.self_update_apply.__module__ == "my_ai.self_update"


def test_self_repair_has_permission_rule():
    assert ("/self-repair/", "self-repair") in api._TOOL_RULES


def test_self_update_api_passes_only_explicit_health_url(monkeypatch):
    seen = {}
    monkeypatch.setattr(api, "require_admin", lambda request: {"id": 1, "username": "test-admin", "role": "admin"})
    monkeypatch.setattr(api, "self_update_apply", lambda **kwargs: seen.update(kwargs) or {"status": "up_to_date"})
    request = api.SelfUpdateRequest(health_url="http://127.0.0.1:8000/health")
    api.self_update_apply_api(request, object())
    assert seen == {"health_url": "http://127.0.0.1:8000/health"}



def test_self_update_api_rejects_remote_health_url(monkeypatch):
    from fastapi import HTTPException
    monkeypatch.setattr(api, "require_admin", lambda request: {"id": 1, "role": "admin"})
    try:
        api.self_update_apply_api(api.SelfUpdateRequest(health_url="https://example.com/health"), object())
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("remote health URL was accepted")
