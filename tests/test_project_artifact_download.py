from pathlib import Path

from my_ai import auth
from my_ai.project_workspace import PROJECTS_ROOT


def login_cookie(user):
    return {"myai_session": auth.create_session(user["id"])}


def test_project_artifact_download_requires_auth_and_returns_file(client_db, tmp_path):
    client = client_db
    user = auth.create_account("owner", "a-secure-password")
    project = PROJECTS_ROOT / "download-contract-test"
    project.mkdir(parents=True, exist_ok=True)
    artifact = project / "EA.mq4"
    artifact.write_text("#property strict\nint OnInit(){return(INIT_SUCCEEDED);}\n", encoding="utf-8")

    unauthenticated = client.get("/projects/file", params={"path": "projects/download-contract-test/EA.mq4"}, follow_redirects=False)
    assert unauthenticated.status_code == 303
    assert "/login" in unauthenticated.headers["location"]

    response = client.get(
        "/projects/file",
        params={"path": "projects/download-contract-test/EA.mq4"},
        cookies=login_cookie(user),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/octet-stream")
    assert response.content.startswith(b"#property strict")
    assert "<!doctype html>" not in response.text.lower()
    assert "ورود | My-AI" not in response.text


def test_project_artifact_download_rejects_paths_outside_projects(client_db, tmp_path):
    client = client_db
    user = auth.create_account("owner", "a-secure-password")
    outside = tmp_path / "secret.mq4"
    outside.write_text("secret", encoding="utf-8")
    response = client.get(
        "/projects/file",
        params={"path": str(outside)},
        cookies=login_cookie(user),
    )
    assert response.status_code == 400
