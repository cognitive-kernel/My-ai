from my_ai.settings_store import SETTING_REGISTRY


def test_observability_retention_settings_exist():
    expected = {"observability.telemetry_enabled", "observability.metrics_retention_days", "observability.trace_retention_days"}
    assert expected <= SETTING_REGISTRY.keys()
    assert all("description" in SETTING_REGISTRY[k] for k in expected)
