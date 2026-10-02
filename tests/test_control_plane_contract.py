from my_ai.control_plane import put_record, get_record, list_history, export_namespace, ensure_schema

def test_control_plane_validates_versions_and_persists_history(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "control.db"))
    import my_ai.config as config
    import my_ai.db as db
    config.settings = config.Settings()
    import importlib
    importlib.reload(db)
    ensure_schema()
    first = put_record("agent.budget", "default", {"version": 1, "steps": 5})
    second = put_record("agent.budget", "default", {"version": 2, "steps": 7})
    assert first["version"] == 1
    assert second["version"] == 2
    assert get_record("agent.budget", "default")["payload"]["steps"] == 7
    history = list_history("agent.budget", "default")
    assert [x["version"] for x in history[:2]] == [2, 1]
    assert export_namespace("agent.budget")["records"][0]["payload"]["steps"] == 7

def test_control_plane_rejects_invalid_version():
    import pytest
    with pytest.raises(ValueError):
        put_record("agent.budget", "invalid", {"version": 0})
