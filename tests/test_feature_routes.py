from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from my_ai.feature_routes import register_routes, _chat_content


class FakeScheduler:
    def __init__(self):
        self.actions = []

    def status(self):
        return {"running": False, "workers": []}

    def stop_learning(self, language):
        self.actions.append(("stop", language))

    def start(self, language):
        self.actions.append(("start", language))


def test_learning_controls_are_registered():
    app = FastAPI()
    scheduler = FakeScheduler()
    register_routes(app, scheduler, lambda request: {"id": 1}, lambda *args: None)
    client = TestClient(app)

    response = client.post("/learning/Python/stop")
    assert response.status_code == 200
    assert scheduler.actions == [("stop", "Python")]


def test_read_only_file_inspection_endpoint(tmp_path: Path):
    target = tmp_path / "note.txt"
    target.write_text("hello", encoding="utf-8")
    app = FastAPI()
    register_routes(app, FakeScheduler(), lambda request: {"id": 1}, lambda *args: None)
    client = TestClient(app)

    response = client.post("/files/inspect", json={"path": str(target)})
    assert response.status_code == 200
    assert response.json()["read_only"] is True
    assert target.read_text(encoding="utf-8") == "hello"


def test_chat_file_generation_rejects_unknown_format():
    app = FastAPI()
    register_routes(app, FakeScheduler(), lambda request: {"id": 1}, lambda *args: None)
    client = TestClient(app)

    response = client.post(
        "/files/generate/from-chat",
        json={"prompt": "test", "format": "exe", "filename": "x.exe"},
    )
    assert response.status_code == 400
    assert "format must be" in response.json()["detail"]


def test_chat_content_preserves_headings_and_lists():
    title, paragraphs, slides = _chat_content("# Project Plan\n\n## Goal\nBuild the API\n- auth\n- tests", "pptx")
    assert title == "Project Plan"
    assert "• auth" in paragraphs
    assert slides
    assert slides[0]["title"] == "Goal"
    assert "Build the API" in slides[0]["body"]
