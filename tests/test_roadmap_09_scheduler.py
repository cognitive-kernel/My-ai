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

def test_scheduler_worker_count_limits_distinct_languages(monkeypatch):
    import my_ai.scheduler as scheduler_module
    class FakeThread:
        def __init__(self, *args, **kwargs):
            self.args = args
        def is_alive(self):
            return True
        def start(self):
            return None
    monkeypatch.setattr(scheduler_module, "fetch_all", lambda *args, **kwargs: [])
    monkeypatch.setattr(scheduler_module, "execute", lambda *args, **kwargs: 0)
    monkeypatch.setattr(scheduler_module.threading, "Thread", FakeThread)
    monkeypatch.setattr(scheduler_module.StudyScheduler, "_ensure_worker_tables", lambda self: None)
    monkeypatch.setattr(scheduler_module.StudyScheduler, "_acquire_lease", lambda self, language: True)
    monkeypatch.setattr(scheduler_module.StudyScheduler, "_release_lease", lambda self, language: None)
    monkeypatch.setattr(scheduler_module, "get_setting", lambda key, default: 1 if key == "scheduler.worker_count" else default)
    scheduler = scheduler_module.StudyScheduler()
    scheduler.start("Python")
    scheduler.start("C")
    assert list(scheduler._workers) == ["python"]


def test_scheduler_concurrency_semaphore_uses_persisted_limit(monkeypatch):
    import my_ai.scheduler as scheduler_module
    monkeypatch.setattr(scheduler_module, "get_setting", lambda key, default: 3 if key == "scheduler.concurrency" else default)
    scheduler = scheduler_module.StudyScheduler()
    assert scheduler._worker_slots.acquire(timeout=0)
    assert scheduler._worker_slots.acquire(timeout=0)
    assert scheduler._worker_slots.acquire(timeout=0)
    assert not scheduler._worker_slots.acquire(timeout=0)
    scheduler._worker_slots.release()
    scheduler._worker_slots.release()
    scheduler._worker_slots.release()


def test_scheduler_retry_backoff_uses_setting(monkeypatch):
    import my_ai.scheduler as scheduler_module
    captured = {}
    class FakeTimer:
        def __init__(self, delay, callback):
            captured["delay"] = delay
            captured["callback"] = callback
        def start(self):
            captured["started"] = True
    monkeypatch.setattr(scheduler_module.threading, "Timer", FakeTimer)
    monkeypatch.setattr(scheduler_module, "fetch_all", lambda *args, **kwargs: [])
    monkeypatch.setattr(scheduler_module, "get_setting", lambda key, default: 7 if key == "scheduler.retry_backoff" else default)
    scheduler = scheduler_module.StudyScheduler()
    scheduler._schedule_worker_recovery("Python", scheduler_module.threading.Event())
    assert captured["started"] is True
    assert captured["delay"] == 7 * (2 ** 3)
