from dataclasses import fields

from my_ai.config import Settings
from my_ai import settings_store


def test_all_environment_backed_settings_have_registry_bridge():
    attrs = {field.name for field in fields(Settings)}
    bridges = {
        key.removeprefix("runtime.")
        for key in settings_store.SETTING_REGISTRY
        if key.startswith("runtime.")
    }
    assert attrs <= bridges


def test_registry_runtime_setting_changes_live_config(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    from my_ai import config
    old = config.settings.ollama_model
    try:
        settings_store.set_setting("runtime.ollama_model", "registry-model")
        assert config.settings.ollama_model == "registry-model"
    finally:
        config.settings.ollama_model = old
        settings_store.delete_setting("runtime.ollama_model")


def test_runtime_secret_is_marked_secret():
    assert settings_store.SETTING_REGISTRY["runtime.openai_api_key"]["secret"] is True

# Registry bridge regression coverage.
