import time
from threading import Event

import pytest

from my_ai.infra.cache import VersionedCache
from my_ai.infra.event_bus import EventBus
from my_ai.infra.execution_budget import BudgetExceeded, ExecutionBudget
from my_ai.infra.parallel import map_independent


def test_event_bus_preserves_subscription_order_and_trace():
    bus = EventBus()
    seen = []
    bus.subscribe("task.done", lambda event: seen.append(("a", event.trace_id)))
    bus.subscribe("task.done", lambda event: seen.append(("b", event.payload["id"])))
    event = bus.publish("task.done", {"id": 7}, trace_id="trace-1")
    assert event.trace_id == "trace-1"
    assert seen == [("a", "trace-1"), ("b", 7)]


def test_execution_budget_enforces_limits():
    budget = ExecutionBudget(max_steps=1, max_tool_calls=1, max_output_tokens=2)
    budget.step()
    budget.tool_call()
    budget.tokens(output_tokens=2)
    with pytest.raises(BudgetExceeded):
        budget.step()


def test_versioned_cache_expires_and_invalidates_versions(monkeypatch):
    cache = VersionedCache()
    key = cache.key("llm", {"prompt": "x"}, version="v1")
    cache.set(key, "ok", ttl=10, version="v1")
    assert cache.get(key, version="v1") == "ok"
    assert cache.get(key, version="v2") is None
    assert cache.invalidate(version="v1") == 1
    assert cache.get(key, version="v1") is None


def test_parallel_map_preserves_input_order_and_isolates_failures():
    def work(value):
        if value == 2:
            raise ValueError("boom")
        return value * 2

    results = map_independent(work, [1, 2, 3], max_workers=2)
    assert [item.index for item in results] == [0, 1, 2]
    assert results[0].value == 2
    assert isinstance(results[1].error, ValueError)
    assert results[2].value == 6


def test_parallel_map_honors_cancellation_before_start():
    cancel = Event()
    cancel.set()
    results = map_independent(lambda value: value * 2, [1, 2, 3], cancel_event=cancel)
    assert all(isinstance(item.error, RuntimeError) for item in results)
    assert all(item.value is None for item in results)
