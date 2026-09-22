from my_ai import api


def test_self_update_api_uses_real_module():
    assert api.self_update_status.__module__ == "my_ai.self_update"
    assert api.self_update_apply.__module__ == "my_ai.self_update"


def test_self_repair_has_permission_rule():
    assert ("/self-repair/", "self-repair") in api._TOOL_RULES


def test_self_update_api_passes_only_explicit_health_url(monkeypatch):
    seen = {}
    monkeypatch.setattr(api, "require_admin", lambda request: {"id": 1, "role": "admin"})
    monkeypatch.setattr(api, "self_update_apply", lambda **kwargs: seen.update(kwargs) or {"status": "up_to_date"})
    request = api.SelfUpdateRequest(health_url="http://127.0.0.1:8000/health")
    api.self_update_apply_api(request, object())
    assert seen == {"health_url": "http://127.0.0.1:8000/health"}

