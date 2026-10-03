from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .metatrader_adapter import bars, indicator, market_context, quote, test_connection
from .software_reproduction import analyze_source


@dataclass(frozen=True)
class CapabilityResult:
    name: str
    available: bool
    evidence: str = ""
    data: dict[str, Any] | None = None
    error: str | None = None


def _software_reproduction(message: str, urls: list[str] | None = None) -> CapabilityResult:
    try:
        targets = list(urls or [])
        if not targets:
            import re
            targets = re.findall(r"https?://[^\\s<>]+", str(message))[:5]
        if not targets:
            return CapabilityResult("software_reproduction", False, error="No authorized HTTP/HTTPS source was provided.")
        specs = [analyze_source(url) for url in targets]
        evidence = "SOFTWARE REPRODUCTION SPECIFICATION (source-derived):\\n" + __import__("json").dumps(specs, ensure_ascii=False, indent=2)[:50000]
        return CapabilityResult("software_reproduction", True, evidence, {"specifications": specs})
    except Exception as exc:
        return CapabilityResult("software_reproduction", False, error=str(exc))


def _metatrader(message: str) -> CapabilityResult:
    try:
        live = market_context(message)
        if live:
            return CapabilityResult("metatrader.market_context", True, live)
        status = test_connection()
        if status.get("connected"):
            return CapabilityResult(
                "metatrader.connection",
                True,
                "LIVE METATRADER CONNECTION:\n" + str(status),
                status,
            )
        return CapabilityResult("metatrader.connection", False, error=str(status.get("error") or "connection failed"))
    except Exception as exc:
        return CapabilityResult("metatrader", False, error=str(exc))


_CAPABILITIES: dict[str, Callable[[str], CapabilityResult]] = {\n    "metatrader": _metatrader,\n}\n

def run(intent: Any, message: str) -> CapabilityResult | None:
    names = tuple(getattr(intent, "intents", ()) or ())
    primary = str(getattr(intent, "name", "") or "")
    if primary and primary not in names:
        names = (primary, *names)
    for name in names:\n        if name == "software_reproduction":\n            urls = list((getattr(intent, "args", {}) or {}).get("urls") or [])\n            return _software_reproduction(message, urls)\n        handler = _CAPABILITIES.get(name)\n        if handler:\n            return handler(message)\n    return None
