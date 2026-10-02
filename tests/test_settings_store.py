from __future__ import annotations

import pytest

from my_ai import settings_store as ss
from my_ai import git_connector
from my_ai import settings_store


def test_github_connector_has_no_api_url_default(monkeypatch):
    monkeypatch.setattr(git_connector, "get_github_settings", lambda: {"api_url": "", "repository": "", "username": "", "token": ""})
    with pytest.raises(RuntimeError, match="API URL"):
        git_connector.GitHubConnector()


def test_github_token_is_saved_through_settings_store(monkeypatch):
    saved = {}
    def fake_set(key, value, *, secret=False): saved[key] = (value, secret)
    monkeypatch.setattr(git_connector, "set_setting", fake_set)
    monkeypatch.setattr(git_connector, "delete_setting", lambda key: saved.pop(key, None))
    assert git_connector.GitHubConnector.save_token("github_pat_example_token_123456") is True
    assert saved["github.token"][0] == "github_pat_example_token_123456"
    assert saved["github.token"][1] is True


def test_settings_secret_roundtrip_uses_encryption(monkeypatch, tmp_path):
    key_path = tmp_path / "settings.key"
    monkeypatch.setattr(settings_store, "KEY_PATH", key_path)
    stored = settings_store._encrypt("secret-value")
    assert stored.startswith(settings_store.SECRET_PREFIX)
    assert settings_store._decrypt(stored) == "secret-value"
    assert stored != "secret-value"


def test_resource_settings_have_expected_defaults(monkeypatch):
    from my_ai import settings_feature
    values = {"resources.cpu_percent": "70", "resources.cpu_threads": "8", "resources.ram_percent": "80", "resources.gpu_layers": "0"}
    monkeypatch.setattr(settings_feature, "get_setting", lambda key, default=None: values.get(key, default))
    monkeypatch.setattr(settings_feature, "get_int", lambda key, default=0: int(values.get(key, default)))
    assert float(settings_feature.get_setting("resources.cpu_percent", "70")) == 70.0
    assert settings_feature.get_int("resources.cpu_threads", 8) == 8
    assert float(settings_feature.get_setting("resources.ram_percent", "80")) == 80.0
    assert settings_feature.get_int("resources.gpu_layers", 0) == 0


def test_settings_registry_validates_and_resets(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "KEY_PATH", tmp_path / "settings.key")
    ss.ensure_schema()
    ss.set_setting("learning.interval_seconds", 120)
    assert ss.get_setting("learning.interval_seconds") == "120"
    with pytest.raises(ValueError): ss.set_setting("learning.interval_seconds", 30)
    assert ss.reset_setting("learning.interval_seconds") == 3600
    assert ss.get_setting("learning.interval_seconds") == "3600"


def test_registered_default_is_returned_after_reset(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "KEY_PATH", tmp_path / "settings.key")
    ss.ensure_schema()
    ss.set_setting("execution.timeout_seconds", 45)
    ss.reset_setting("execution.timeout_seconds")
    assert ss.get_setting("execution.timeout_seconds") == "10"


def test_registered_settings_export_import_is_validated(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "KEY_PATH", tmp_path / "settings.key")
    ss.ensure_schema()
    ss.set_setting("execution.timeout_seconds", 25)
    exported = ss.export_registered_settings()
    assert exported["execution.timeout_seconds"] == "25"
    imported = dict(exported); imported["execution.timeout_seconds"] = 40
    result = ss.import_registered_settings(imported)
    assert result["execution.timeout_seconds"] == "40"
    with pytest.raises(ValueError, match="Unknown registered settings"): ss.import_registered_settings({"not.registered": 1})
    with pytest.raises(ValueError): ss.import_registered_settings({"execution.timeout_seconds": 0})


def test_custom_llm_registry_secret_is_not_exported(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "KEY_PATH", tmp_path / "settings.key")
    ss.ensure_schema()
    ss.set_setting("llm.provider", "custom-openai-compatible")
    ss.set_setting("llm.custom.base_url", "http://127.0.0.1:9000")
    ss.set_setting("llm.custom.model", "my-model")
    ss.set_setting("llm.custom.api_key", "secret-key", secret=True)
    assert ss.get_setting("llm.custom.api_key") == "secret-key"
    assert "llm.custom.api_key" not in ss.export_registered_settings()


def test_configuration_schema_is_versioned_and_migrated(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "KEY_PATH", tmp_path / "settings.key")
    ss.ensure_schema()
    expected_version = ss.CONFIG_SCHEMA_VERSION
    assert ss.get_configuration_schema_version() == expected_version
    assert ss.migrate_configuration() == expected_version
    with ss.connect() as conn:
        row = conn.execute("SELECT version FROM app_settings_migrations ORDER BY version DESC LIMIT 1").fetchone()
        assert int(row["version"]) == expected_version
        columns = {str(item["name"]) for item in conn.execute("PRAGMA table_info(app_settings)").fetchall()}
        assert "schema_version" in columns
    ss.set_setting("execution.timeout_seconds", 25)
    with ss.connect() as conn:
        row = conn.execute("SELECT schema_version FROM app_settings WHERE key=?", ("execution.timeout_seconds",)).fetchone()
        assert int(row["schema_version"]) == ss.SETTING_REGISTRY["execution.timeout_seconds"]["version"]


def test_registry_setting_updates_runtime_configuration(tmp_path, monkeypatch):
    import sqlite3
    from my_ai import config
    def connect():
        conn = sqlite3.connect(tmp_path / "runtime.db")
        conn.row_factory = sqlite3.Row
        return conn
    monkeypatch.setattr(ss, "connect", connect)
    original = config.settings.llm_retry_attempts
    ss.ensure_schema()
    ss.set_setting("llm.retry_attempts", 4)
    assert config.settings.llm_retry_attempts == 4
    config.settings.llm_retry_attempts = original

def test_persisted_registry_setting_is_reapplied_on_startup(tmp_path, monkeypatch):
    import sqlite3
    from my_ai import config
    def connect():
        conn = sqlite3.connect(tmp_path / "persisted.db")
        conn.row_factory = sqlite3.Row
        return conn
    monkeypatch.setattr(ss, "connect", connect)
    ss.ensure_schema()
    ss.set_setting("llm.retry_attempts", 5)
    config.settings.llm_retry_attempts = 1
    ss.apply_persisted_settings()
    assert config.settings.llm_retry_attempts == 5

def test_registry_exposes_category_dependencies_and_delete_semantics(monkeypatch, tmp_path):
    monkeypatch.setattr(ss, "KEY_PATH", tmp_path / "settings.key")
    ss.ensure_schema()
    registry = ss.get_setting_registry()
    assert registry["llm.provider"]["category"] == "llm"
    assert registry["llm.provider"]["depends_on"] == []
    ss.SETTING_REGISTRY["test.dependent"] = {"version": 1, "type": "text", "default": "", "description": "", "depends_on": ["llm.provider"]}
    try:
        ss.set_setting("test.dependent", "x")
        assert ss.get_setting("test.dependent") == "x"
    finally:
        ss.SETTING_REGISTRY.pop("test.dependent", None)


def test_observability_configuration_settings_are_registered():
    from my_ai.settings_store import SETTING_REGISTRY
    for key in ("observability.alert_rules", "observability.notification_destinations", "observability.dashboard_config", "observability.diagnostics_export"):
        assert key in SETTING_REGISTRY
