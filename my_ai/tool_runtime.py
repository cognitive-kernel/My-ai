from __future__ import annotations

import concurrent.futures
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolExecution:
    trace_id: str
    tool: str
    status: str
    result: Any = None
    error: str = ""
    elapsed_ms: float = 0.0


def _validate(payload: Any, schema: dict[str, Any]) -> None:
    if not isinstance(schema, dict):
        raise ValueError("input schema must be an object")
    if schema.get("type") in (None, "object") and not isinstance(payload, dict):
        raise ValueError("tool input must be an object")
    required = schema.get("required") or []
    if isinstance(required, list):
        missing = [str(name) for name in required if not isinstance(payload, dict) or name not in payload]
        if missing:
            raise ValueError("missing required tool input: " + ", ".join(missing))
    properties = schema.get("properties") or {}
    if isinstance(properties, dict) and isinstance(payload, dict):
        for name, rule in properties.items():
            if name not in payload or not isinstance(rule, dict):
                continue
            expected = rule.get("type")
            value = payload[name]
            if expected == "string" and not isinstance(value, str):
                raise ValueError(f"{name} must be a string")
            if expected == "number" and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise ValueError(f"{name} must be a number")
            if expected == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
                raise ValueError(f"{name} must be an integer")
            if expected == "boolean" and not isinstance(value, bool):
                raise ValueError(f"{name} must be a boolean")


def execute_registered_tool(
    *,
    name: str,
    input_payload: Any,
    input_schema: dict[str, Any],
    execute: Callable[[Any], Any],
    authorize: Callable[[str], bool],
    observe: Callable[[ToolExecution], None] | None = None,
    audit: Callable[[ToolExecution], None] | None = None,
    timeout_seconds: float = 30.0,
    trace_id: str | None = None,
) -> ToolExecution:
    trace = trace_id or str(uuid.uuid4())
    started = time.perf_counter()

    def finish(status: str, result: Any = None, error: str = "") -> ToolExecution:
        item = ToolExecution(trace, name, status, result, error, round((time.perf_counter() - started) * 1000, 2))
        if observe:
            observe(item)
        if audit:
            audit(item)
        return item

    try:
        _validate(input_payload, input_schema)
        if not authorize(name):
            return finish("denied", error="tool authorization denied")
        timeout = float(timeout_seconds)
        if timeout <= 0 or timeout > 300:
            raise ValueError("timeout_seconds must be > 0 and <= 300")
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(execute, input_payload)
            try:
                result = future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                future.cancel()
                return finish("timeout", error=f"tool execution exceeded {timeout:g}s")
        return finish("completed", result=result)
    except Exception as exc:
        return finish("failed", error=str(exc))
