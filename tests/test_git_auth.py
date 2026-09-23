import pytest

from my_ai.git_connector import GitHubConnector


def test_environment_token_is_not_used(monkeypatch):
    monkeypatch.setattr(GitHubConnector, "_gh_executable", staticmethod(lambda: None))
    monkeypatch.setenv("GITHUB_TOKEN", "github_pat_TEST_TOKEN")
    monkeypatch.setattr("my_ai.git_connector.get_github_settings", lambda: {"api_url":"https://api.example.test","repository":"","username":"","token":""})
    assert GitHubConnector.token_source() == "none"
    assert GitHubConnector(token="x", api_url="https://api.example.test")._effective_token() == "x"


def test_saved_token_is_used_from_database_settings(monkeypatch):
    monkeypatch.setattr(GitHubConnector, "_gh_executable", staticmethod(lambda: None))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("my_ai.git_connector.get_github_settings", lambda: {"api_url":"https://api.example.test","repository":"","username":"","token":"github_pat_SAVED_TEST"})
    assert GitHubConnector.oauth_available() is True
    assert GitHubConnector.token_source() == "saved"
    assert GitHubConnector()._headers()["Authorization"] == "Bearer github_pat_SAVED_TEST"


def test_missing_api_url_is_configuration_error(monkeypatch):
    monkeypatch.setattr("my_ai.git_connector.get_github_settings", lambda: {"api_url":"","repository":"","username":"","token":"token"})
    with pytest.raises(RuntimeError, match="API URL"):
        GitHubConnector()
