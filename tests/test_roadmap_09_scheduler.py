from my_ai.settings_store import SETTING_REGISTRY


def test_scheduler_has_runtime_resource_controls():
    expected = {"scheduler.worker_count", "scheduler.concurrency", "scheduler.default_priority", "scheduler.retry_backoff", "scheduler.interval_seconds"}
    assert expected <= SETTING_REGISTRY.keys()
    assert all(SETTING_REGISTRY[k]["version"] >= 2 for k in expected)
