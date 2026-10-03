from __future__ import annotations

from typing import Any

from .mt4 import quote as mt4_quote, status as mt4_status
from ..settings_store import get_setting, get_bool


def _config() -> dict[str, Any]:
    return {
        "enabled": get_bool("domain.mt4mt5.enabled", False),
        "version": str(get_setting("domain.mt4mt5.version", "MT4") or "MT4").upper(),
        "install_path": str(get_setting("domain.mt4mt5.install_path", "") or "").strip(),
        "account": str(get_setting("domain.mt4mt5.account", "") or "").strip(),
        "password": str(get_setting("domain.mt4mt5.password", "") or ""),
        "server": str(get_setting("domain.mt4mt5.server", "") or "").strip(),
    }


def _mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError as exc:
        raise RuntimeError("MT5 support is not installed. Install the optional metatrader dependency.") from exc
    return mt5


def _mt5_initialize():
    cfg = _config()
    if not cfg["enabled"]:
        raise RuntimeError("MetaTrader capability is disabled in Settings.")
    mt5 = _mt5()
    kwargs: dict[str, Any] = {}
    if cfg["install_path"]:
        kwargs["path"] = cfg["install_path"]
    if cfg["account"]:
        kwargs["login"] = int(cfg["account"])
    if cfg["password"]:
        kwargs["password"] = cfg["password"]
    if cfg["server"]:
        kwargs["server"] = cfg["server"]
    if not mt5.initialize(**kwargs):
        code = mt5.last_error()
        raise RuntimeError(f"MT5 initialize failed: {code}")
    return mt5


def quote(symbol: str) -> dict[str, Any]:
    cfg = _config()
    if cfg["version"] == "MT4":
        return mt4_quote(symbol)
    mt5 = _mt5_initialize()
    try:
        name = str(symbol or "").strip().upper().replace("/", "").replace("_", "").replace("-", "")
        if not name:
            raise ValueError("symbol is required")
        if not mt5.symbol_select(name, True):
            raise RuntimeError(f"MT5 symbol is not available: {name}")
        tick = mt5.symbol_info_tick(name)
        if tick is None:
            raise RuntimeError(f"MT5 returned no tick for {name}")
        info = mt5.symbol_info(name)
        return {
            "source": "mt5",
            "symbol": name,
            "bid": float(tick.bid),
            "ask": float(tick.ask),
            "last": float(tick.last),
            "timestamp": int(tick.time),
            "account": cfg["account"],
            "server": cfg["server"],
            "digits": int(info.digits) if info is not None else None,
            "point": float(info.point) if info is not None else None,
        }
    finally:
        mt5.shutdown()


def status() -> dict[str, Any]:
    cfg = _config()
    if not cfg["enabled"]:
        return {"enabled": False, "connected": False, "version": cfg["version"], "reason": "disabled"}
    if cfg["version"] == "MT4":
        return {"version": "MT4", **mt4_status()}
    mt5 = _mt5_initialize()
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        return {
            "enabled": True,
            "connected": True,
            "version": "MT5",
            "terminal": {
                "name": getattr(terminal, "name", None),
                "path": getattr(terminal, "path", None),
                "build": getattr(terminal, "build", None),
            } if terminal else None,
            "account": {
                "login": getattr(account, "login", None),
                "server": getattr(account, "server", None),
                "balance": getattr(account, "balance", None),
            } if account else None,
        }
    finally:
        mt5.shutdown()
