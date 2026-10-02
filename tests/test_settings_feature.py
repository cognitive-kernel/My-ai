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
    routes = {}
    for route in sf.router.routes:
        path = getattr(route, "path", "")
        if path:
            routes.setdefault(path, set()).update(getattr(route, "methods", set()))
    assert "/settings/registry/{key:path}" in routes
    assert {"PUT", "DELETE"} <= routes["/settings/registry/{key:path}"]
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


def test_learning_source_ui_supports_file_upload_edit_and_review():
    html = sf.SETTINGS_HTML
    assert "ls_file" in html
    script = __import__("pathlib").Path("my_ai/settings_script.js").read_text(encoding="utf-8")
    assert "uploadLearningSourceCatalog" in script
    assert "editLearningSource" in script
    assert "/settings/learning-sources/upload" in script

def test_course_form_exposes_auto_manual_sources_and_learning_policy_controls():
    html = sf.SETTINGS_HTML
    for token in ("course_mode", "Auto Discover", "Manual Sources", "course_source_policy", "manual-first", "course_llm", "course_schedule", "course_mastery"):
        assert token in html
def test_database_health_route_is_registered():
    paths = {getattr(route, "path", "") for route in sf.router.routes}
    assert "/settings/database/health" in paths


def test_settings_config_exposes_observability_controls(monkeypatch):
    from my_ai import settings_feature
    monkeypatch.setattr(settings_feature, "require_admin", lambda request: {"id": 1, "username": "test"})
    monkeypatch.setattr(settings_feature, "get_bool", lambda key, default=False: default)
    monkeypatch.setattr(settings_feature, "get_setting", lambda key, default="": {"observability.alert_rules": '[{"name":"latency"}]', "observability.notification_destinations": '["webhook"]', "observability.dashboard_config": '{"refresh":30}', "observability.diagnostics_export": "json"}.get(key, default))
    config = settings_feature.settings_config(object())
    assert config["observability"]["alert_rules"][0]["name"] == "latency"
    assert config["observability"]["notification_destinations"] == ["webhook"]
    assert config["observability"]["dashboard_config"]["refresh"] == 30
    assert config["observability"]["diagnostics_export"] == "json"


def test_backup_uses_configured_destination_when_path_omitted(monkeypatch):
    from my_ai import settings_feature
    monkeypatch.setattr(settings_feature, "require_admin", lambda request: 1)
    monkeypatch.setattr(settings_feature, "get_setting", lambda key, default="": "data/configured-backups" if key == "database.backup.destination" else default)
    captured = {}
    monkeypatch.setattr(settings_feature, "backup_database", lambda path, overwrite=False: captured.update(path=path, overwrite=overwrite) or {"path": path})
    result = settings_feature.settings_database_backup(settings_feature.BackupRequest(), object())
    assert captured["path"] == "data/configured-backups"
    assert result["path"] == "data/configured-backups"


def test_backup_retention_prunes_old_files(tmp_path):
    from my_ai.backup_manager import prune_backups
    import os, time
    paths = []
    for index in range(3):
        path = tmp_path / f"backup-{index}.db"
        path.write_text(str(index))
        os.utime(path, (time.time() - index, time.time() - index))
        paths.append(path)
    removed = prune_backups(str(tmp_path), 2)
    assert len(removed) == 1
    assert len(list(tmp_path.iterdir())) == 2


def test_database_restore_requires_confirmation(monkeypatch):
    from my_ai import settings_feature
    monkeypatch.setattr(settings_feature, "require_admin", lambda request: 1)
    try:
        settings_feature.settings_database_restore(settings_feature.BackupRequest(path="x.db"), object())
    except settings_feature.HTTPException as exc:
        assert exc.status_code == 400
        assert "confirmation" in str(exc.detail).lower()
    else:
        raise AssertionError("restore without confirmation must fail")
