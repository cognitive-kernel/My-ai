from __future__ import annotations

import time
from typing import Any

from .settings_store import get_int, get_setting


DEFAULT_CPU_PERCENT = 70.0
DEFAULT_CPU_THREADS = 8
DEFAULT_RAM_PERCENT = 80.0
DEFAULT_GPU_LAYERS = 0


def limits() -> dict[str, float | int]:
    return {
        "cpu_percent": max(1.0, min(100.0, float(get_setting("resources.cpu_percent", str(DEFAULT_CPU_PERCENT)))),
        "cpu_threads": max(1, min(128, get_int("resources.cpu_threads", DEFAULT_CPU_THREADS))),
        "ram_percent": max(1.0, min(100.0, float(get_setting("resources.ram_percent", str(DEFAULT_RAM_PERCENT)))),
        "gpu_layers": max(0, min(128, get_int("resources.gpu_layers", DEFAULT_GPU_LAYERS))),
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
    """Continuously observe host load before an inference starts.

    CPU percentage and RAM percentage are host-load gates; Ollama receives the
    configured thread/GPU-layer limits separately. This avoids claiming that a
    process can reserve an exact percentage of a host's CPU or RAM when the
    backend does not expose such a quota.
    """
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
