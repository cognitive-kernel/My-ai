from my_ai import api


def test_self_update_api_uses_real_module():
    assert api.self_update_status.__module__ == "my_ai.self_update"
    assert api.self_update_apply.__module__ == "my_ai.self_update"


def test_self_repair_has_permission_rule():
    assert ("/self-repair/", "self-repair") in api._TOOL_RULES


def test_self_update_request_has_explicit_health_url():
    field = api.SelfUpdateRequest.model_fields["health_url"]
    assert field.annotation is not None

