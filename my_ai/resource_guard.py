from __future__ import annotations

import time
import os
from typing import Any

from .settings_store import get_setting

DEFAULT_CPU_PERCENT = 70.0
DEFAULT_CPU_THREADS = 8
DEFAULT_RAM_PERCENT = 80.0
DEFAULT_GPU_LAYERS = 0


def _setting(key: str, env_name: str, default: str) -> str:
    return str(get_setting(key, os.getenv(env_name, default)))


def _number(key: str, env_name: str, default: float, low: float, high: float) -> float:
    try:
        value = float(_setting(key, env_name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(low, min(high, value))


def limits() -> dict[str, float | int]:
    return {
        "cpu_percent": _number("resources.cpu_percent", "RESOURCES_CPU_PERCENT", DEFAULT_CPU_PERCENT, 1.0, 100.0),
        "cpu_threads": max(1, min(128, int(float(_setting("resources.cpu_threads", "RESOURCES_CPU_THREADS", str(DEFAULT_CPU_THREADS)))))),
        "ram_percent": _number("resources.ram_percent", "RESOURCES_RAM_PERCENT", DEFAULT_RAM_PERCENT, 1.0, 100.0),
        "gpu_layers": max(0, min(128, int(float(_setting("resources.gpu_layers", "RESOURCES_GPU_LAYERS", str(DEFAULT_GPU_LAYERS)))))),
    }


def snapshot() -> dict[str, Any]:
    cfg = limits()
    try:
        import psutil
        cpu = float(psutil.cpu_percent(interval=0.05))
        vm = psutil.virtual_memory()
        return {
            "cpu_percent": round(cpu, 1),
            "ram_percent": round(float(vm.percent), 1),
            "ram_used_bytes": int(vm.used),
            "ram_total_bytes": int(vm.total),
            "cpu_limit_percent": cfg["cpu_percent"],
            "cpu_threads": cfg["cpu_threads"],
            "ram_limit_percent": cfg["ram_percent"],
            "gpu_layers": cfg["gpu_layers"],
            "within_limits": cpu <= float(cfg["cpu_percent"]) and float(vm.percent) <= float(cfg["ram_percent"]),
        }
    except Exception as exc:
        return {
            "cpu_percent": None,
            "ram_percent": None,
            "cpu_limit_percent": cfg["cpu_percent"],
            "cpu_threads": cfg["cpu_threads"],
            "ram_limit_percent": cfg["ram_percent"],
            "gpu_layers": cfg["gpu_layers"],
            "within_limits": True,
            "monitor_error": str(exc),
        }


def wait_until_available(stop_event=None, *, max_wait: float | None = None) -> dict[str, Any]:
    """Continuously observe host load before an inference starts."""
    started = time.monotonic()
    while True:
        state = snapshot()
        if state.get("within_limits"):
            return state
        if stop_event is not None and stop_event.is_set():
            raise InterruptedError("learning stopped while waiting for hardware resources")
        if max_wait is not None and time.monotonic() - started >= max_wait:
            return state
        if stop_event is not None:
            stop_event.wait(1.0)
        else:
            time.sleep(1.0)
