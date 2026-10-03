"""Read-only MetaTrader 4 market-data capability.

The connector never fabricates a quote. MT4 publishes the latest tick through a
small local bridge file under the configured terminal's MQL4/Files directory.
The AI runtime reads that bridge and returns the broker/terminal quote.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..settings_store import get_bool, get_setting


class MT4Unavailable(RuntimeError):
    """MT4 is configured but no fresh terminal quote is available."""


@dataclass(frozen=True)
class MT4Quote:
    symbol: str
    bid: float
    ask: float
    timestamp: float
    account: str = ""
    server: str = ""

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0


def _config() -> dict[str, Any]:
    return {
        "enabled": get_bool("mt4.enabled", False),
        "install_path": str(get_setting("mt4.install_path", "") or "").strip(),
        "library_path": str(get_setting("mt4.library_path", "") or "").strip(),
        "account": str(get_setting("mt4.account", "") or "").strip(),
        "server": str(get_setting("mt4.server", "") or "").strip(),
        "bridge_file": str(get_setting("mt4.bridge_file", "MQL4/Files/my_ai_tick.json") or "").strip(),
        "max_age_seconds": max(1.0, float(get_setting("mt4.max_tick_age_seconds", 10))),
    }


def _candidate_paths(cfg: dict[str, Any]) -> list[Path]:
    candidates: list[Path] = []
    bridge = Path(cfg["bridge_file"]).expanduser()
    for root_key in ("install_path", "library_path"):
        root = str(cfg[root_key] or "").strip()
        if not root:
            continue
        base = Path(root).expanduser()
        candidates.append((base / bridge).resolve())
        if bridge.name:
            candidates.append((base / "MQL4" / "Files" / bridge.name).resolve())
    # A configured bridge_file may itself be absolute.
    if bridge.is_absolute():
        candidates.insert(0, bridge.resolve())
    seen: set[str] = set()
    return [p for p in candidates if not (str(p) in seen or seen.add(str(p)))]


def _read_payload(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise MT4Unavailable(f"MT4 bridge file could not be read: {path}") from exc
    if not isinstance(raw, dict):
        raise MT4Unavailable("MT4 bridge payload must be a JSON object.")
    return raw


def quote(symbol: str = "AUDUSD") -> dict[str, Any]:
    cfg = _config()
    if not cfg["enabled"]:
        raise MT4Unavailable("MT4 capability is disabled in Settings.")
    paths = _candidate_paths(cfg)
    if not paths:
        raise MT4Unavailable("MT4 install path is not configured.")
    existing = next((p for p in paths if p.is_file()), None)
    if existing is None:
        raise MT4Unavailable("No MT4 tick bridge is publishing data yet.")
    payload = _read_payload(existing)
    actual_symbol = str(payload.get("symbol") or "").replace("/", "").replace("_", "").replace("-", "").upper()
    requested = str(symbol or "").replace("/", "").replace("_", "").replace("-", "").upper()
    if actual_symbol and requested and actual_symbol != requested:
        raise MT4Unavailable(f"MT4 bridge is publishing {actual_symbol}, not {requested}.")
    try:
        bid = float(payload["bid"])
        ask = float(payload["ask"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MT4Unavailable("MT4 bridge payload has no numeric bid/ask.") from exc
    timestamp = float(payload.get("timestamp") or existing.stat().st_mtime)
    age = max(0.0, time.time() - timestamp)
    if age > cfg["max_age_seconds"]:
        raise MT4Unavailable(f"MT4 tick is stale ({age:.1f}s old).")
    if bid <= 0 or ask <= 0 or ask < bid:
        raise MT4Unavailable("MT4 bridge returned an invalid bid/ask.")
    return {
        "source": "mt4",
        "symbol": actual_symbol or requested,
        "bid": bid,
        "ask": ask,
        "mid": (bid + ask) / 2.0,
        "timestamp": timestamp,
        "age_seconds": round(age, 3),
        "account": str(payload.get("account") or cfg["account"]),
        "server": str(payload.get("server") or cfg["server"]),
        "bridge_file": str(existing),
    }


def status() -> dict[str, Any]:
    cfg = _config()
    if not cfg["enabled"]:
        return {"enabled": False, "connected": False, "reason": "disabled"}
    try:
        data = quote("AUDUSD")
        return {"enabled": True, "connected": True, "quote": data}
    except MT4Unavailable as exc:
        return {
            "enabled": True,
            "connected": False,
            "install_path": cfg["install_path"],
            "account": cfg["account"],
            "server": cfg["server"],
            "reason": str(exc),
        }
