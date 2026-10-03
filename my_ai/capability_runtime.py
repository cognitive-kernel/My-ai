from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .tool_runtime import execute_registered_tool


@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    input_schema: dict[str, Any]
    permission: str
    handler: Callable[[dict[str, Any]], Any]
    timeout_seconds: float = 30.0


_CAPABILITIES: dict[str, Capability] = {}


def register_capability(
    name: str,
    description: str,
    input_schema: dict[str, Any],
    permission: str,
    handler: Callable[[dict[str, Any]], Any],
    timeout_seconds: float = 30.0,
) -> None:
    key = str(name).strip()
    if not key:
        raise ValueError("Capability name is required.")
    _CAPABILITIES[key] = Capability(
        name=key,
        description=description,
        input_schema=input_schema,
        permission=permission,
        handler=handler,
        timeout_seconds=timeout_seconds,
    )


def list_capabilities() -> list[dict[str, Any]]:
    return [
        {
            "name": item.name,
            "description": item.description,
            "input_schema": item.input_schema,
            "permission": item.permission,
            "timeout_seconds": item.timeout_seconds,
        }
        for item in _CAPABILITIES.values()
    ]


def run(
    name: str,
    payload: dict[str, Any],
    *,
    authorize: Callable[[str], bool] | None = None,
) -> dict[str, Any]:
    capability = _CAPABILITIES.get(str(name).strip())
    if capability is None:
        return {"status": "failed", "error": f"Unknown capability: {name}"}

    execution = execute_registered_tool(
        name=capability.name,
        input_payload=payload,
        input_schema=capability.input_schema,
        execute=capability.handler,
        authorize=authorize or (lambda _permission: True),
        timeout_seconds=capability.timeout_seconds,
    )
    return {
        "status": execution.status,
        "trace_id": execution.trace_id,
        "result": execution.result,
        "error": execution.error,
        "elapsed_ms": execution.elapsed_ms,
    }


def _register_builtin_capabilities() -> None:
    from .domain.metatrader import quote

    register_capability(
        "market.quote",
        "Read a live quote from the configured MetaTrader terminal/account.",
        {
            "type": "object",
            "required": ["symbol"],
            "properties": {"symbol": {"type": "string"}},
        },
        "market.read",
        lambda payload: quote(str(payload["symbol"])),
        timeout_seconds=15.0,
    )


_register_builtin_capabilities()
