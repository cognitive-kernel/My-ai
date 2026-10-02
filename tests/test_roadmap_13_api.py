from my_ai.settings_store import SETTING_REGISTRY


def test_server_operational_settings_are_registry_backed():
    expected = {"server.host", "server.port", "server.cors_origins", "server.session_timeout", "server.upload_limit_mb", "server.request_timeout", "server.rate_limit_per_minute", "server.maintenance_mode", "server.readiness_policy"}
    assert expected <= SETTING_REGISTRY.keys()


def test_runtime_host_uses_environment_when_server_host_is_unset(monkeypatch):
    from my_ai import __main__ as main_module
    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setattr(main_module, "has_setting", lambda key: False)
    monkeypatch.setattr(main_module, "get_setting", lambda key, default: default)
    captured = {}
    monkeypatch.setattr(main_module.uvicorn, "run", lambda app, **kwargs: captured.update(kwargs))
    main_module.run_server()
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 8000
