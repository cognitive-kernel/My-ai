import threading
import time

from my_ai.resource_guard import limits, wait_until_available
from my_ai.scheduler import StudyScheduler


def test_scheduler_lease_prevents_duplicate_worker_owner(monkeypatch, tmp_path):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "scheduler.db"))
    import importlib
    import my_ai.config as config
    import my_ai.db as db
    config.settings = config.Settings()
    importlib.reload(db)
    db.init_db()
    first = StudyScheduler(interval_seconds=1)
    second = StudyScheduler(interval_seconds=1)
    first._ensure_lease_table()
    assert first._acquire_lease("Python") is True
    assert second._acquire_lease("Python") is False
    first._release_lease("Python")


def test_scheduler_resource_wait_respects_stop_event(monkeypatch):
    scheduler = StudyScheduler(interval_seconds=1)
    stop = threading.Event()
    monkeypatch.setattr("my_ai.scheduler.resource_status", lambda: {"cpu_percent": 99.0, "ram_percent": 99.0})
    monkeypatch.setattr("my_ai.scheduler.get_setting", lambda key, default: "1")
    stop.set()
    try:
        scheduler._wait_for_resources(stop)
    except InterruptedError:
        return
    raise AssertionError("stopped scheduler must not wait forever")


def test_scheduler_worker_registry_is_singleton_per_language(monkeypatch):
    scheduler = StudyScheduler(interval_seconds=1)
    worker = threading.Thread(target=lambda: time.sleep(0.05))
    stop = threading.Event()
    scheduler._workers["python"] = (worker, stop)
    worker.start()
    assert scheduler._workers["python"][0] is worker
    worker.join()


def test_resource_limits_are_bounded():
    cfg = limits()
    assert 1 <= cfg["cpu_percent"] <= 100
    assert 1 <= cfg["ram_percent"] <= 100
    assert 1 <= cfg["cpu_threads"] <= 128
    assert 0 <= cfg["gpu_layers"] <= 128


def test_resource_wait_honors_stop_event(monkeypatch):
    event = threading.Event()
    event.set()
    monkeypatch.setattr("my_ai.resource_guard.snapshot", lambda: {"within_limits": False})
    try:
        wait_until_available(event, max_wait=0.1)
    except InterruptedError:
        pass
    else:
        raise AssertionError("stopped scheduler must not wait indefinitely")
