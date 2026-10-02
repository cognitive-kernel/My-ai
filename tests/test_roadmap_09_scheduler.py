from my_ai.settings_store import SETTING_REGISTRY


def test_scheduler_has_runtime_resource_controls():
    expected = {"scheduler.worker_count", "scheduler.concurrency", "scheduler.default_priority", "scheduler.retry_backoff", "scheduler.interval_seconds"}
    assert expected <= SETTING_REGISTRY.keys()
    assert all(SETTING_REGISTRY[k]["version"] >= 2 for k in expected - {"scheduler.interval_seconds"})
    assert SETTING_REGISTRY["scheduler.interval_seconds"]["version"] >= 1


def test_scheduler_endpoint_uses_persisted_interval_setting(monkeypatch):
    from my_ai import api
    monkeypatch.setattr(api, "require_user", lambda request: {"id": 1, "role": "admin"})
    monkeypatch.setattr(api, "get_int", lambda key, default: 900)
    monkeypatch.setattr(api.scheduler, "start", lambda language: None)
    result = api.scheduler_start(type("R", (), {"interval_seconds": 3600, "language": "Python"})(), object())
    assert result["interval_seconds"] == 900