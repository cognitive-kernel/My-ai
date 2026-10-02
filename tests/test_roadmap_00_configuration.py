from my_ai.settings_store import SETTING_REGISTRY


def test_configuration_registry_has_schema_metadata_and_sensitive_flags():
    assert SETTING_REGISTRY
    required = {"version", "type", "default", "description"}
    assert all(required <= set(spec) for spec in SETTING_REGISTRY.values())
    assert SETTING_REGISTRY["llm.custom.api_key"]["secret"] is True
    assert SETTING_REGISTRY["agent.max_steps"]["min"] <= SETTING_REGISTRY["agent.max_steps"]["default"] <= SETTING_REGISTRY["agent.max_steps"]["max"]


def test_configuration_versions_are_positive():
    assert all(int(spec["version"]) >= 1 for spec in SETTING_REGISTRY.values())
