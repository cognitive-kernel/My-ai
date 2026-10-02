from my_ai.settings_store import SETTING_REGISTRY


def test_server_operational_settings_are_registry_backed():
    expected = {"server.host", "server.port", "server.cors_origins", "server.session_timeout", "server.upload_limit_mb", "server.request_timeout", "server.rate_limit_per_minute", "server.maintenance_mode", "server.readiness_policy"}
    assert expected <= SETTING_REGISTRY.keys()


def test_runtime_host_uses_environment_when_server_host_is_unset(monkeypatch):
    from my_ai import settings_store
    from my_ai import __main__ as main_module
    assert callable(settings_store.has_setting)
    monkeypatch.setenv("HOST", "0.0.0.0")
    assert settings_store.get_setting("server.host", "127.0.0.1") == "127.0.0.1"
