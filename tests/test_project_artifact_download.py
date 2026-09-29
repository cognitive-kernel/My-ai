import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from my_ai import auth, db
from my_ai.api import app
from my_ai.project_workspace import PROJECTS_ROOT


@pytest.fixture()
def client_db(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "api.db"))
    db.init_db()
    try:
        yield TestClient(app)
    finally:
        object.__setattr__(db.settings, "db_path", old)


def login_cookie(user):
    return {"myai_session": auth.create_session(user["id"])}


def test_project_artifact_download_requires_auth_and_returns_file(client_db):
    client = client_db
    user = auth.create_account("owner", "a-secure-password")
    project = PROJECTS_ROOT / "download-contract-test"
    project.mkdir(parents=True, exist_ok=True)
    artifact = project / "EA.mq4"
    artifact.write_text("#property strict\nint OnInit(){return(INIT_SUCCEEDED);}\n", encoding="utf-8")
    try:
        unauthenticated = client.get(
            "/projects/file",
            params={"path": "projects/download-contract-test/EA.mq4"},
            follow_redirects=False,
        )
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
    finally:
        shutil.rmtree(project, ignore_errors=True)


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

def test_chat_ui_does_not_classify_messages_with_static_keyword_lists():
    source = Path("my_ai/ui_extensions.py").read_text(encoding="utf-8")
    assert "learning=bool(re.search" not in source
    assert "image=bool(re.search" not in source
    assert "بساز.*تصویر" not in source

def test_project_build_result_exposes_dynamic_artifact_links():
    from my_ai.agent import Agent

    answer = Agent._format_project_build_result({
        "status": "build_failed",
        "project_path": "projects/mt4-ea",
        "project_name": "mt4-ea",
        "files": ["EA.mq4", "README.md"],
        "build": {"passed": False, "error": "MetaEditor unavailable"},
    })
    assert "[[MYAI_FILE|EA.mq4|" in answer
    assert "/projects/file?path=projects%2Fmt4-ea%2FEA.mq4" in answer
    assert "MetaEditor unavailable" in answer
