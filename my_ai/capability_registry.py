from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class CapabilitySpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    permission: str
    timeout_seconds: float
    resource_budget: dict[str, float | int]
    health_check: Callable[[], dict[str, Any]] | None = None
    verifier: Callable[[Any], bool] | None = None


_REGISTRY: dict[str, CapabilitySpec] = {}


def register(spec: CapabilitySpec) -> CapabilitySpec:
    if not spec.name.strip():
        raise ValueError("Capability name is required")
    if spec.timeout_seconds <= 0:
        raise ValueError("Capability timeout must be positive")
    _REGISTRY[spec.name] = spec
    return spec


def get(name: str) -> CapabilitySpec | None:
    return _REGISTRY.get(str(name).strip())


def discover(*, permission: str | None = None) -> list[dict[str, Any]]:
    items = []
    for spec in _REGISTRY.values():
        if permission and spec.permission != permission:
            continue
        item = asdict(spec)
        item["health_check"] = bool(spec.health_check)
        item["verifier"] = bool(spec.verifier)
        items.append(item)
    return sorted(items, key=lambda x: x["name"])


def _validate_schema(value: Any, schema: Mapping[str, Any], path: str = "$") -> None:
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            raise TypeError(f"{path} must be an object")
        for key in schema.get("required", []):
            if key not in value:
                raise ValueError(f"Missing required input: {path}.{key}")
        for key, child in (schema.get("properties") or {}).items():
            if key in value:
                _validate_schema(value[key], child, f"{path}.{key}")
    elif expected == "string" and not isinstance(value, str):
        raise TypeError(f"{path} must be a string")
    elif expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        raise TypeError(f"{path} must be an integer")
    elif expected == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
        raise TypeError(f"{path} must be a number")
    elif expected == "boolean" and not isinstance(value, bool):
        raise TypeError(f"{path} must be a boolean")
    elif expected == "array" and not isinstance(value, list):
        raise TypeError(f"{path} must be an array")


def validate_input(name: str, value: dict[str, Any]) -> None:
    spec = get(name)
    if spec is None:
        raise KeyError(f"Unknown capability: {name}")
    if not isinstance(value, dict):
        raise TypeError("Capability input must be an object")
    _validate_schema(value, spec.input_schema)

def health(name: str) -> dict[str, Any]:
    spec = get(name)
    if spec is None:
        return {"name": name, "healthy": False, "error": "unknown capability"}
    if spec.health_check is None:
        return {"name": name, "healthy": True, "health_check": "not-configured"}
    try:
        result = dict(spec.health_check())
        result.setdefault("name", name)
        result.setdefault("healthy", True)
        return result
    except Exception as exc:
        return {"name": name, "healthy": False, "error": str(exc)}


def verify(name: str, value: Any) -> bool:
    spec = get(name)
    if spec is None or spec.verifier is None:
        return False
    try:
        return bool(spec.verifier(value))
    except Exception:
        return False
