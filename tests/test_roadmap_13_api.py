from my_ai.settings_store import SETTING_REGISTRY


def test_server_operational_settings_are_registry_backed():
    expected = {"server.host", "server.port", "server.cors_origins", "server.session_timeout", "server.upload_limit_mb", "server.request_timeout", "server.rate_limit_per_minute", "server.maintenance_mode", "server.readiness_policy"}
    assert expected <= SETTING_REGISTRY.keys()
