from fastapi.testclient import TestClient
from my_ai.api import app
def test_health():
    with TestClient(app) as client:
        r=client.get("/health"); assert r.status_code==200; assert r.json()["status"]=="ok"
def test_home():
    with TestClient(app) as client: assert client.get("/", follow_redirects=False).status_code==303


def test_github_logout_does_not_use_removed_yes_flag(monkeypatch):
    import my_ai.api as api
    calls=[]
    class R:
        returncode=0
        stdout=""
        stderr=""
    monkeypatch.setattr(api.GitHubConnector, "save_token", lambda token: calls.append(("token", token)))
    monkeypatch.setattr(api.GitHubConnector, "_gh_executable", classmethod(lambda cls: "gh"))
    monkeypatch.setattr(api.subprocess, "run", lambda *args, **kwargs: (calls.append((args, kwargs)) or R()))
    result=api.git_logout()
    argv=calls[1][0][0]
    assert "--yes" not in argv
    assert kwargs_input(calls[1][1]) == "y\n"
    assert result["authenticated"] is False


def kwargs_input(kwargs):
    return kwargs.get("input")
