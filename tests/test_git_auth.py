import os

from my_ai.git_connector import GitHubConnector


def test_environment_token_is_used_without_gh(monkeypatch, tmp_path):
    monkeypatch.setattr(GitHubConnector, "_gh_executable", staticmethod(lambda: None))
    monkeypatch.setenv("GITHUB_TOKEN", "github_pat_TEST_TOKEN")
    monkeypatch.setenv("MYAI_GITHUB_TOKEN_FILE", str(tmp_path / "missing-token"))
    monkeypatch.delenv("MYAI_GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    assert GitHubConnector.token_source() == "environment"
    assert GitHubConnector.token_status() is True
    assert GitHubConnector()._effective_token() == "github_pat_TEST_TOKEN"


def test_saved_token_is_used_without_oauth_client(monkeypatch, tmp_path):
    token_file = tmp_path / "token"
    token_file.write_text("github_pat_SAVED_TEST", encoding="utf-8")
    monkeypatch.setattr(GitHubConnector, "_gh_executable", staticmethod(lambda: None))
    monkeypatch.setenv("MYAI_GITHUB_TOKEN_FILE", str(token_file))
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("MYAI_GITHUB_CLIENT_ID", raising=False)
    monkeypatch.delenv("GITHUB_CLIENT_ID", raising=False)
    assert GitHubConnector.oauth_available() is True
    assert GitHubConnector.token_source() == "saved"
    assert GitHubConnector()._headers()["Authorization"] == "Bearer github_pat_SAVED_TEST"
