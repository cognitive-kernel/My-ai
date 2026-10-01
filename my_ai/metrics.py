from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any

_lock = threading.Lock()
_counts: defaultdict[str, int] = defaultdict(int)
_totals: defaultdict[str, float] = defaultdict(float)


def record_http_request(method: str, path: str, status: int, duration: float) -> None:
    key = f"http:{method.upper()}:{path}"
    with _lock:
        _counts[key] += 1
        _totals[f"{key}:duration"] += max(0.0, duration)
        _counts[f"{key}:status:{int(status)}"] += 1


def record_http_error(path: str) -> None:
    with _lock:
        _counts[f"http_errors:{path}"] += 1

def record_inference(provider: str, model: str, duration: float, *, prompt_tokens: int | None = None, output_tokens: int | None = None) -> None:
    key = f"{provider}:{model}"
    with _lock:
        _counts[f"inference:{key}"] += 1
        _totals[f"duration:{key}"] += max(0.0, duration)
        if prompt_tokens is not None:
            _totals[f"prompt_tokens:{key}"] += max(0, prompt_tokens)
        if output_tokens is not None:
            _totals[f"output_tokens:{key}"] += max(0, output_tokens)

def record_route(task: str, model: str, reason: str) -> None:
    with _lock:
        _counts[f"routing:{task}:{model}:{reason}"] += 1

def record_error(provider: str, model: str) -> None:
    with _lock:
        _counts[f"errors:{provider}:{model}"] += 1

def snapshot() -> dict[str, Any]:
    with _lock:
        inference = {}
        for key, count in _counts.items():
            if not key.startswith("inference:"):
                continue
            name = key.split(":", 1)[1]
            inference[name] = {
                "requests": count,
                "errors": _counts.get(f"errors:{name}", 0),
                "total_seconds": round(_totals.get(f"duration:{name}", 0.0), 3),
                "avg_seconds": round(_totals.get(f"duration:{name}", 0.0) / count, 3) if count else 0.0,
                "prompt_tokens": int(_totals.get(f"prompt_tokens:{name}", 0)),
                "output_tokens": int(_totals.get(f"output_tokens:{name}", 0)),
            }
        http = {}
        for key, count in _counts.items():
            if not key.startswith("http:"):
                continue
            name = key[5:]
            path = name.split(":", 1)[1] if ":" in name else name
            http[name] = {
                "requests": count,
                "avg_seconds": round(_totals.get(f"{key}:duration", 0.0) / count, 4) if count else 0.0,
                "errors": _counts.get(f"http_errors:{path}", 0),
            }
        routing = {key[8:]: count for key, count in _counts.items() if key.startswith("routing:")}\n        return {"inference": inference, "http": http, "routing": routing}

def timer():
    return time.perf_counter()
