from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable
import json
import re

from .capability_registry import CapabilitySpec, register, validate_input
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


_CAPABILITIES: dict[str, Callable[[str], CapabilityResult]] = {"metatrader": _metatrader}


def run(intent: Any, message: str) -> CapabilityResult | None:
    names = tuple(getattr(intent, "intents", ()) or ())
    primary = str(getattr(intent, "name", "") or "")
    if primary and primary not in names:
        names = (primary, *names)
    for name in names:
        if name == "software_reproduction":
            validate_input(name, {"message": message})
            args = getattr(intent, "args", {}) or {}
            return _software_reproduction(message, list(args.get("urls") or []), str(args.get("project_path") or ""))
        handler = _CAPABILITIES.get(name)
        if handler:
            return handler(message)
    return None


register(CapabilitySpec(
    name="metatrader",
    description="Read authorized MT4/MT5 market and indicator data.",
    input_schema={"type": "object", "required": ["message"]},
    output_schema={"type": "object"},
    permission="metatrader.read",
    timeout_seconds=30,
    resource_budget={"cpu_percent": 20, "ram_mb": 512, "tool_calls": 5},
))
register(CapabilitySpec(
    name="software_reproduction",
    description="Analyze an authorized software/site source and produce an independent reconstruction workspace.",
    input_schema={"type": "object", "required": ["message"]},
    output_schema={"type": "object"},
    permission="software.reproduction",
    timeout_seconds=60,
    resource_budget={"cpu_percent": 50, "ram_mb": 1024, "tool_calls": 10},
))
