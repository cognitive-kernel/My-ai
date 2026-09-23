from my_ai.git_connector import GitHubConnector


def test_whoami_uses_user_endpoint(monkeypatch):
    seen = {}

    def fake_request(self, method, path, **kwargs):
        seen["method"] = method
        seen["path"] = path
        return {"login": "test-user", "name": "Test User"}

    monkeypatch.setattr(GitHubConnector, "_request", fake_request)
    identity = GitHubConnector(token="test-token", api_url="https://api.github.com").whoami()
    assert identity["login"] == "test-user"
    assert seen == {"method": "GET", "path": "/user"}
