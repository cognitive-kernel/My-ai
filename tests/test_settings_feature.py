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
    sf.execute("DELETE FROM app_settings WHERE key=?", ("migration.legacy_cisco_cleanup_v1",))
    sf.execute("INSERT OR IGNORE INTO custom_courses(name,description) VALUES(?,?)", ("Cisco", "legacy"))
    sf._setup()
    assert not sf.fetch_all("SELECT id FROM custom_courses WHERE lower(name)=lower(?)", ("Cisco",))


def test_settings_requires_authentication():
    with TestClient(app) as client:
        response = client.get("/settings")
        assert response.status_code in {200, 401}


def test_adding_topic_reduces_completed_course_progress():
    sf._setup()
    course_id = sf.execute("INSERT INTO custom_courses(name,description) VALUES(?,?)", ("Test Course", "test"))
    sf.execute(
        "INSERT INTO custom_course_topics(course_id,topic_order,title,goal) VALUES(?,?,?,?)",
        (course_id, 1, "Initial Topic", "Initial goal"),
    )
    sf.execute(
        "INSERT INTO custom_course_progress(course_id,topic_id) SELECT ?,id FROM custom_course_topics WHERE course_id=?",
        (course_id, course_id),
    )
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
    course_id = sf.execute("INSERT INTO custom_courses(name,description) VALUES(?,?)", ("Attempt Course", "test"))
    topic_id = sf.execute("INSERT INTO custom_course_topics(course_id,topic_order,title,goal) VALUES(?,?,?,?)", (course_id, 1, "Topic", "Goal"))
    sf.execute("INSERT INTO custom_course_progress(course_id,topic_id) VALUES(?,?)", (course_id, topic_id))
    topic = sf._progress(course_id)[0]
    sf.execute("UPDATE custom_course_progress SET last_attempt_at=CURRENT_TIMESTAMP WHERE topic_id=?", (int(topic["id"]),))
    updated = sf._progress(course_id)[0]
    assert updated["last_attempt_at"]


def test_settings_registry_update_route_exists():
    routes = {getattr(route, "path", ""): getattr(route, "methods", set()) for route in sf.router.routes}
    assert "/settings/registry/{key:path}" in routes
    assert "PUT" in routes["/settings/registry/{key:path}"]
    assert "/settings/registry/export" in routes
    assert "/settings/registry/import" in routes


def test_learning_source_form_exposes_type_priority_weight_and_review_controls():
    html = sf.SETTINGS_HTML
    for field in ("ls_url", "ls_type", "ls_priority", "ls_weight"):
        assert "id='" + field + "'" in html
    script = __import__("pathlib").Path("my_ai/settings_script.js").read_text(encoding="utf-8")
    assert "reviewLearningSource" in script
    assert "weight:Number(byId(\"ls_weight\").value||1)" in script


def test_configuration_registry_ui_is_schema_driven():
    script = __import__("pathlib").Path("my_ai/settings_script.js").read_text(encoding="utf-8")
    assert "j.items||[]" in script
    assert "registryInput(x)" in script
    assert "x.choices||[]" in script
    assert "x.default" in script
    assert "updateRegisteredSetting" in script
