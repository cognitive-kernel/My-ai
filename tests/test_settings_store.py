from __future__ import annotations

import pytest

from my_ai import git_connector
from my_ai import settings_store


def test_github_connector_has_no_api_url_default(monkeypatch):
    monkeypatch.setattr(git_connector, "get_github_settings", lambda: {
        "api_url": "",
        "repository": "",
        "username": "",
        "token": "",
    })
    with pytest.raises(RuntimeError, match="API URL"):
        git_connector.GitHubConnector()


def test_github_token_is_saved_through_settings_store(monkeypatch):
    saved = {}

    def fake_set(key, value, *, secret=False):
        saved[key] = (value, secret)

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
    try:
        ss.set_setting("learning.interval_seconds", 30)
    except ValueError:
        pass
    else:
        raise AssertionError("out-of-range registered setting must fail")
    assert ss.reset_setting("learning.interval_seconds") == 3600
    assert ss.get_setting("learning.interval_seconds") == 3600
