import pytest

from my_ai.git_connector import GitHubConnector


def test_environment_token_is_not_used(monkeypatch):
    monkeypatch.setattr(GitHubConnector, "_gh_executable", staticmethod(lambda: None))
    monkeypatch.setattr(GitHubConnector, "_gcm_token", classmethod(lambda cls: None))
    monkeypatch.setenv("GITHUB_TOKEN", "github_pat_TEST_TOKEN")
    monkeypatch.setattr("my_ai.git_connector.get_github_settings", lambda: {"api_url":"https://api.github.com","repository":"","username":"","token":""})
    assert GitHubConnector.token_source() == "none"
    assert GitHubConnector(token="x", api_url="https://api.github.com")._effective_token() == "x"


def test_saved_token_is_used_from_database_settings(monkeypatch):
    monkeypatch.setattr(GitHubConnector, "_gh_executable", staticmethod(lambda: None))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr("my_ai.git_connector.get_github_settings", lambda: {"api_url":"https://api.github.com","repository":"","username":"","token":"github_pat_SAVED_TEST"})
    assert GitHubConnector.oauth_available() is True
    assert GitHubConnector.token_source() == "saved"
    assert GitHubConnector()._headers()["Authorization"] == "Bearer github_pat_SAVED_TEST"


def test_missing_api_url_is_configuration_error(monkeypatch):
    monkeypatch.setattr("my_ai.git_connector.get_github_settings", lambda: {"api_url":"","repository":"","username":"","token":"token"})
    with pytest.raises(RuntimeError, match="API URL"):
        GitHubConnector()


def test_untrusted_api_url_is_rejected(monkeypatch):
    monkeypatch.setattr("my_ai.git_connector.get_github_settings", lambda: {"api_url":"https://evil.example","repository":"","username":"","token":"token"})
    with pytest.raises(ValueError, match="api.github.com"):
        GitHubConnector()


def test_environment_token_never_wins_over_settings(monkeypatch):
    monkeypatch.setattr(GitHubConnector, "_gh_executable", staticmethod(lambda: None))
    monkeypatch.setattr(GitHubConnector, "_gcm_token", classmethod(lambda cls: None))
    monkeypatch.setenv("GITHUB_TOKEN", "github_pat_ENVIRONMENT_TOKEN")
    monkeypatch.setattr("my_ai.git_connector.get_github_settings", lambda: {"api_url":"https://api.github.com","repository":"","username":"","token":""})
    connector = GitHubConnector()
    assert connector._effective_token() is None
