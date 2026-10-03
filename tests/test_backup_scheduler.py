from my_ai.scheduler import StudyScheduler


def test_backup_schedule_parsing():
    assert StudyScheduler._backup_interval_seconds("manual") is None
    assert StudyScheduler._backup_interval_seconds("hourly") == 3600
    assert StudyScheduler._backup_interval_seconds("daily") == 86400
    assert StudyScheduler._backup_interval_seconds("weekly") == 604800
    assert StudyScheduler._backup_interval_seconds("every:120") == 120
    assert StudyScheduler._backup_interval_seconds("every:1") == 60


def test_scheduled_backup_uses_settings(monkeypatch, tmp_path):
    scheduler = StudyScheduler()
    calls = {}

    def fake_backup(path):
        calls["path"] = path
        return {"path": path}

    def fake_prune(destination, retention):
        calls["retention"] = (destination, retention)
        return []

    monkeypatch.setattr("my_ai.scheduler.get_setting", lambda key, default=None: {
        "database.backup_destination": str(tmp_path),
        "database.backup_retention": 4,
    }.get(key, default))
    monkeypatch.setattr("my_ai.scheduler.backup_database", fake_backup)
    monkeypatch.setattr("my_ai.scheduler.prune_backups", fake_prune)

    result = scheduler.run_scheduled_backup_once()
    assert result["path"].startswith(str(tmp_path))
    assert result["path"].endswith(".db")
    assert calls["retention"] == (str(tmp_path), 4)
