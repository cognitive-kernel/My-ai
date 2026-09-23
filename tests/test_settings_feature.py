from fastapi.testclient import TestClient

from my_ai.api import app
from my_ai import settings_feature as sf


def test_settings_router_has_declared_routes():
    assert any(getattr(route, "path", "") == "/settings" for route in sf.router.routes)


def test_settings_and_learning_routes_are_registered():
    with TestClient(app):
        paths = {getattr(route, "path", "") for route in app.routes}
        assert "/settings" in paths
        assert "/learning" in paths
        assert "/settings/courses" in paths
        assert "/learning/active" in paths


def test_settings_feature_can_register_directly():
    sf.install(app)
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/settings" in paths


def test_default_cisco_course_is_seeded():
    sf._setup()
    rows = sf.fetch_all("SELECT id,name FROM custom_courses WHERE lower(name)=lower(?)", ("Cisco",))
    assert rows
    items = sf._progress(int(rows[0]["id"]))
    assert len(items) == len(sf.DEFAULT_TOPICS)
    assert items[0]["status"] in {"planned", "started", "paused", "completed"}


def test_course_summary_reports_current_topic_and_fractional_progress():
    sf._setup()
    course = sf.fetch_all("SELECT id FROM custom_courses WHERE lower(name)=lower(?)", ("Cisco",))[0]
    course_id = int(course["id"])
    topic = sf._progress(course_id)[0]
    sf._set_topic(int(topic["id"]), "started", 25, "lesson")
    summary = sf._summary(course_id)
    assert summary["current"]["title"] == sf.DEFAULT_TOPICS[0][0]
    assert summary["current"]["phase"] == "lesson"
    assert summary["progress_percent"] > 0


def test_settings_requires_authentication():
    with TestClient(app) as client:
        response = client.get("/settings")
        assert response.status_code in {303, 401}
