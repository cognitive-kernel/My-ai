from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .metatrader_adapter import bars, indicator, market_context, quote, test_connection


@dataclass(frozen=True)
class CapabilityResult:
    name: str
    available: bool
    evidence: str = ""
    data: dict[str, Any] | None = None
    error: str | None = None


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


_CAPABILITIES: dict[str, Callable[[str], CapabilityResult]] = {
    "metatrader": _metatrader,
}


def run(intent: Any, message: str) -> CapabilityResult | None:
    names = tuple(getattr(intent, "intents", ()) or ())
    primary = str(getattr(intent, "name", "") or "")
    if primary and primary not in names:
        names = (primary, *names)
    for name in names:
        handler = _CAPABILITIES.get(name)
        if handler:
            return handler(message)
    return None
