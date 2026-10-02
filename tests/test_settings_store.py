from __future__ import annotations

import pytest

import my_ai.settings_store as ss


def test_custom_llm_registry_secret_is_not_exported(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "KEY_PATH", tmp_path / "settings.key")
    ss.ensure_schema()
    ss.set_setting("llm.provider", "custom-openai-compatible")
    ss.set_setting("llm.custom.base_url", "http://127.0.0.1:9000")
    ss.set_setting("llm.custom.model", "my-model")
    ss.set_setting("llm.custom.api_key", "secret-key", secret=True)
    assert ss.get_setting("llm.custom.api_key") == "secret-key"
    exported = ss.export_registered_settings()
    assert "llm.custom.api_key" not in exported


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
