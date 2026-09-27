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


def test_legacy_cisco_course_is_purged():
    sf.execute("INSERT OR IGNORE INTO custom_courses(name,description) VALUES(?,?)", ("Cisco", "legacy"))
    sf._setup()
    assert not sf.fetch_all("SELECT id FROM custom_courses WHERE lower(name)=lower(?)", ("Cisco",))


def test_settings_requires_authentication():
    with TestClient(app) as client:
        response = client.get("/settings")
        assert response.status_code in {200, 401}


def test_adding_topic_reduces_completed_course_progress():
    sf._setup()
    course_id = int(sf.fetch_all("SELECT id FROM custom_courses WHERE lower(name)=lower(?)", ("Python",))[0]["id"])
    rows = sf._progress(course_id)
    for row in rows:
        sf._set_topic(int(row["id"]), "completed", 100, "completed")
    assert sf._summary(course_id)["progress_percent"] == 100.0
    next_order = max(int(x["topic_order"]) for x in rows) + 1
    topic_id = sf.execute(
        "INSERT INTO custom_course_topics(course_id,topic_order,title,goal) VALUES(?,?,?,?)",
        (course_id, next_order, "New Topic", "Learn the new topic"),
    )
    sf.execute("INSERT INTO custom_course_progress(course_id,topic_id) VALUES(?,?)", (course_id, topic_id))
    summary = sf._summary(course_id)
    assert summary["progress_percent"] < 100
    assert summary["completed_topics"] == summary["total_topics"] - 1
    assert summary["current"]["status"] == "planned"


def test_custom_course_progress_tracks_last_attempt_column():
    sf._setup()
    course_id = int(sf.fetch_all("SELECT id FROM custom_courses WHERE lower(name)=lower(?)", ("Cisco",))[0]["id"])
    topic = sf._progress(course_id)[0]
    sf.execute("UPDATE custom_course_progress SET last_attempt_at=CURRENT_TIMESTAMP WHERE topic_id=?", (int(topic["id"]),))
    updated = sf._progress(course_id)[0]
    assert updated["last_attempt_at"]
