from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import json
import re

from .capability_registry import CapabilitySpec, register, discover, get, validate_input, verify
from .metatrader_adapter import market_context, test_connection
from .software_reproduction import analyze_source
from .reproduction_builder import generate_workspace


@dataclass(frozen=True)
class CapabilityResult:
    name: str
    available: bool
    evidence: str = ""
    data: dict[str, Any] | None = None
    error: str | None = None


def _software_reproduction(message: str, urls: list[str] | None = None, project_path: str = "") -> CapabilityResult:
    try:
        targets = list(urls or []) or re.findall(r"https?://[^\s<>]+", str(message))[:5]
        if not targets:
            return CapabilityResult("software_reproduction", False, error="No authorized HTTP/HTTPS source was provided.")
        specs = [analyze_source(url) for url in targets]
        generated = [generate_workspace(spec, project_path) for spec in specs] if project_path else []
        evidence = "SOFTWARE REPRODUCTION SPECIFICATION (source-derived):\n" + json.dumps(specs, ensure_ascii=False, indent=2)[:50000]
        return CapabilityResult("software_reproduction", True, evidence, {"specifications": specs, "generated_workspaces": generated})
    except Exception as exc:
        return CapabilityResult("software_reproduction", False, error=str(exc))


def _metatrader(message: str) -> CapabilityResult:
    try:
        live = market_context(message)
        if live:
            return CapabilityResult("metatrader.market_context", True, live)
        status = test_connection()
        if status.get("connected"):
            return CapabilityResult("metatrader.connection", True, "LIVE METATRADER CONNECTION:\n" + json.dumps(status, ensure_ascii=False, default=str), status)
        return CapabilityResult("metatrader.connection", False, error=str(status.get("error") or "connection failed"))
    except Exception as exc:
        return CapabilityResult("metatrader", False, error=str(exc))


def _delegated(name: str, message: str) -> CapabilityResult:
    return CapabilityResult(name, True, f"CAPABILITY DELEGATION: {name} is handled by the specialized Agent workflow.", {"request": str(message)[:20000]})


_CAPABILITIES: dict[str, Callable[[str], CapabilityResult]] = {
    "metatrader": _metatrader,
    "coding": lambda message: _delegated("coding", message),
    "research": lambda message: _delegated("research", message),
    "files": lambda message: _delegated("files", message),
    "multimodal": lambda message: _delegated("multimodal", message),
}


def run(intent: Any, message: str) -> CapabilityResult | None:
    names = tuple(getattr(intent, "intents", ()) or ())
    primary = str(getattr(intent, "name", "") or "")
    if primary and primary not in names:
        names = (primary, *names)
    for name in names:
        spec = get(name)
        if name == "software_reproduction":
            args = getattr(intent, "args", {}) or {}
            try:
                validate_input(name, {"message": message})
                result = _software_reproduction(
                    message,
                    list(args.get("urls") or []),
                    str(args.get("project_path") or ""),
                )
                if result.available and spec and spec.verifier and not verify(name, result.data or {}):
                    return CapabilityResult(result.name, False, error="Capability verification failed.")
                return result
            except Exception as exc:
                return CapabilityResult(name, False, error=str(exc))
        handler = _CAPABILITIES.get(name)
        if handler and spec:
            try:
                validate_input(name, {"message": message})
                result = handler(message)
                if result.available and spec.verifier and not verify(name, result.data or {}):
                    return CapabilityResult(result.name, False, error="Capability verification failed.")
                return result
            except Exception as exc:
                return CapabilityResult(name, False, error=str(exc))
    return None


def _health_metatrader() -> dict[str, Any]:
    try:
        status = test_connection()
        return {"healthy": bool(status.get("connected")), "version": status.get("version"), "connected": bool(status.get("connected"))}
    except Exception as exc:
        return {"healthy": False, "error": str(exc)}


def _health_local() -> dict[str, Any]:
    return {"healthy": True, "runtime": "available"}


def _verify_result(value: Any) -> bool:
    return isinstance(value, dict) and bool(
        value.get("source") or value.get("specifications") or value.get("request") is not None
    )


def _register(name: str, description: str, permission: str, timeout: float, budget: dict[str, Any], health_check=None) -> None:
    register(CapabilitySpec(
        name=name,
        description=description,
        input_schema={"type": "object", "required": ["message"]},
        output_schema={"type": "object"},
        permission=permission,
        timeout_seconds=timeout,
        resource_budget=budget,
        verifier=_verify_result,
        health_check=health_check or _health_local,
    ))


_register("metatrader", "Read authorized MT4/MT5 market and indicator data.", "metatrader.read", 30, {"cpu_percent": 20, "ram_mb": 512, "tool_calls": 5}, _health_metatrader)
_register("software_reproduction", "Analyze an authorized software/site source and produce an independent reconstruction workspace.", "software.reproduction", 60, {"cpu_percent": 50, "ram_mb": 1024, "tool_calls": 10})
_register("coding", "Specialized software implementation and project generation.", "coding.execute", 300, {"cpu_percent": 70, "ram_mb": 4096, "tool_calls": 30})
_register("research", "Multi-source research with provenance and verification.", "research.read", 120, {"cpu_percent": 40, "ram_mb": 2048, "tool_calls": 20})
_register("files", "Authorized local file inspection and processing.", "files.read", 60, {"cpu_percent": 30, "ram_mb": 1024, "tool_calls": 10})
_register("multimodal", "Authorized image/audio/multimodal analysis.", "multimodal.read", 120, {"cpu_percent": 50, "ram_mb": 2048, "tool_calls": 10})
