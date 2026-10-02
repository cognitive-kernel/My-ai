from my_ai.settings_store import get_setting_registry, get_configuration_schema_version


def test_configuration_registry_is_single_schema_source():
    registry = get_setting_registry()
    assert registry
    assert isinstance(registry, dict)
    assert get_configuration_schema_version() >= 1
    assert all("version" in spec and "type" in spec for spec in registry.values())
