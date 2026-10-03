from __future__ import annotations

import os
from typing import Any

from .resource_guard import limits, snapshot
from .settings_store import get_float


DEFAULT_PROFILES = {
    "chat": {"seconds": 30.0, "cpu_threads": 2, "ram_percent": 35.0, "max_tokens": 2048, "concurrency": 2},
    "coding": {"seconds": 300.0, "cpu_threads": 6, "ram_percent": 70.0, "max_tokens": 12000, "concurrency": 1},
    "reasoning": {"seconds": 180.0, "cpu_threads": 6, "ram_percent": 65.0, "max_tokens": 10000, "concurrency": 1},
    "market": {"seconds": 60.0, "cpu_threads": 3, "ram_percent": 50.0, "max_tokens": 5000, "concurrency": 2},
}


def hardware_profile() -> dict[str, Any]:
    state = snapshot()
    return {
        "cpu_count": os.cpu_count() or 1,
        "cpu_threads_available": int(limits()["cpu_threads"]),
        "ram_total_bytes": state.get("ram_total_bytes"),
        "ram_used_bytes": state.get("ram_used_bytes"),
        "gpu_layers": int(limits()["gpu_layers"]),
        "backend_policy": "CPU-first; GPU only when backend explicitly supports configured layers.",
    }


def budget_for(task: str) -> dict[str, Any]:
    kind = str(task or "chat").strip().lower()
    base = dict(DEFAULT_PROFILES.get(kind, DEFAULT_PROFILES["chat"]))
    key = f"agent.resource_budget.{kind}_seconds"
    base["seconds"] = get_float(key, float(base["seconds"]))
    host = snapshot()
    if host.get("ram_percent") is not None and float(host["ram_percent"]) > 90:
        base["concurrency"] = 1
        base["max_tokens"] = min(int(base["max_tokens"]), 2048)
    if kind == "coding" and int(limits()["cpu_threads"]) < 4:
        base["max_tokens"] = min(int(base["max_tokens"]), 6000)
    return {"task": kind, "budget": base, "hardware": hardware_profile()}


def choose_task_budget(task: str) -> dict[str, Any]:
    result = budget_for(task)
    result["admission"] = {
        "allowed": bool(result["budget"]["seconds"] > 0 and result["budget"]["cpu_threads"] > 0),
        "reason": "hardware-aware task budget",
    }
    return result
