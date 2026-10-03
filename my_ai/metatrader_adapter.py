from __future__ import annotations

import importlib
import logging
from datetime import datetime, timezone
from typing import Any

from .settings_store import get_bool, get_setting

log = logging.getLogger(__name__)

_TF = {
    "M1": "TIMEFRAME_M1", "M5": "TIMEFRAME_M5", "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30", "H1": "TIMEFRAME_H1", "H4": "TIMEFRAME_H4", "D1": "TIMEFRAME_D1",
}


def config() -> dict[str, Any]:
    return {
        "enabled": get_bool("domain.mt4mt5.enabled", False),
        "version": str(get_setting("domain.mt4mt5.version", "MT5")),
        "install_path": str(get_setting("domain.mt4mt5.install_path", "")),
        "account": str(get_setting("domain.mt4mt5.account", "")),
        "password": str(get_setting("domain.mt4mt5.password", "", secret=True)),
        "server": str(get_setting("domain.mt4mt5.server", "")),
        "timeframe": str(get_setting("domain.mt4mt5.timeframe", "M15")),
        "tick_data": get_bool("domain.mt4mt5.tick_data", True),
        "indicators": get_bool("domain.mt4mt5.indicators", True),
        "market_analysis": get_bool("domain.mt4mt5.market_analysis", True),
        "trading": get_bool("domain.mt4mt5.trading", False),
        "api_version": str(get_setting("domain.mt4mt5.api_version", "v1")),
        "bridge_url": str(get_setting("domain.mt4mt5.bridge_url", "http://127.0.0.1:8765")),
    }


def _mt5():
    try:
        return importlib.import_module("MetaTrader5")
    except ImportError as exc:
        raise RuntimeError("MetaTrader5 package is not installed. Run: pip install MetaTrader5") from exc


def _initialize_mt5():
    c = config()
    mt5 = _mt5()
    kwargs: dict[str, Any] = {"timeout": 60000}
    if c["account"].strip():
        kwargs["login"] = int(c["account"])
    if c["password"]:
        kwargs["password"] = c["password"]
    if c["server"].strip():
        kwargs["server"] = c["server"]
    path = c["install_path"].strip()
    ok = mt5.initialize(path=path, **kwargs) if path else mt5.initialize(**kwargs)
    if not ok:
        err = mt5.last_error()
        mt5.shutdown()
        raise RuntimeError(f"MetaTrader 5 initialize failed: {err}")
    return mt5


def _close_mt5(mt5) -> None:
    try:
        mt5.shutdown()
    except Exception:
        pass


def _json_value(value: Any) -> Any:
    if hasattr(value, "_asdict"):
        return {k: _json_value(v) for k, v in value._asdict().items()}
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _mt5_quote(symbol: str) -> dict[str, Any]:
    mt5 = _initialize_mt5()
    try:
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Unable to select symbol: {symbol}")
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"No tick data for symbol: {symbol}; error={mt5.last_error()}")
        info = mt5.symbol_info(symbol)
        return {
            "source": "mt5",
            "symbol": symbol,
            "tick": _json_value(tick),
            "symbol_info": _json_value(info) if info else None,
            "account": _json_value(mt5.account_info()),
            "terminal": _json_value(mt5.terminal_info()),
        }
    finally:
        _close_mt5(mt5)


def _mt5_bars(symbol: str, timeframe: str, count: int) -> dict[str, Any]:
    mt5 = _initialize_mt5()
    try:
        tf_name = _TF.get(timeframe.upper())
        if not tf_name or not hasattr(mt5, tf_name):
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Unable to select symbol: {symbol}")
        rows = mt5.copy_rates_from_pos(symbol, getattr(mt5, tf_name), 0, count)
        if rows is None:
            raise RuntimeError(f"No bars returned: {mt5.last_error()}")
        return {"source": "mt5", "symbol": symbol, "timeframe": timeframe.upper(), "bars": _json_value(rows)}
    finally:
        _close_mt5(mt5)


def _bridge_request(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    import httpx
    url = config()["bridge_url"].rstrip("/") + path
    with httpx.Client(timeout=10.0) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


def test_connection() -> dict[str, Any]:
    c = config()
    if not c["enabled"]:
        return {"connected": False, "version": c["version"], "error": "MT4/MT5 adapter is disabled"}
    if c["version"].upper() == "MT5":
        mt5 = _initialize_mt5()
        try:
            return {
                "connected": True,
                "version": "MT5",
                "terminal": _json_value(mt5.terminal_info()),
                "account": _json_value(mt5.account_info()),
                "version_info": _json_value(mt5.version()),
            }
        finally:
            _close_mt5(mt5)
    result = _bridge_request("/status", {"account": c["account"], "server": c["server"], "api_version": c["api_version"]})
    return {"version": "MT4", **result}


def quote(symbol: str) -> dict[str, Any]:
    c = config()
    if not c["enabled"]:
        raise RuntimeError("MT4/MT5 adapter is disabled")
    if c["version"].upper() == "MT5":
        return _mt5_quote(symbol)
    return _bridge_request("/quote", {"symbol": symbol, "timeframe": c["timeframe"], "api_version": c["api_version"]})


def bars(symbol: str, timeframe: str | None = None, count: int = 100) -> dict[str, Any]:
    c = config()
    timeframe = (timeframe or c["timeframe"]).upper()
    count = max(1, min(int(count), 5000))
    if c["version"].upper() == "MT5":
        return _mt5_bars(symbol, timeframe, count)
    return _bridge_request("/bars", {"symbol": symbol, "timeframe": timeframe, "count": count, "api_version": c["api_version"]})


def indicator(symbol: str, name: str, timeframe: str | None = None, params: list[Any] | None = None, buffer: int = 0, shift: int = 0) -> dict[str, Any]:
    c = config()
    if not c["indicators"]:
        raise RuntimeError("Indicator access is disabled")
    payload = {
        "symbol": symbol, "name": name, "timeframe": (timeframe or c["timeframe"]).upper(),
        "params": params or [], "buffer": int(buffer), "shift": int(shift), "api_version": c["api_version"],
    }
    # Custom indicators are terminal-side objects. Both MT4 and MT5 therefore
    # use the same local bridge contract for iCustom-style buffer reads.
    return _bridge_request("/indicator", payload)

def market_context(message: str) -> str:
    """Return compact live MT context for the chat agent when a symbol is present."""
    text = str(message or "")
    if not config()["enabled"]:
        return ""
    import re
    symbols = re.findall(r"(?<![A-Za-z])[A-Z]{6,10}(?:\.[A-Z0-9]+)?(?![A-Za-z])", text.upper())
    symbol = symbols[0] if symbols else ""
    if not symbol:
        return ""
    wants_indicator = any(x in text.casefold() for x in ("rsi", "macd", "ema", "sma", "moving average", "atr", "اندیکاتور", "شاخص"))
    wants_market = any(x in text.casefold() for x in ("price", "quote", "bid", "ask", "قیمت", "بازار", "نرخ", "تیک", "tick"))
    if not (wants_indicator or wants_market):
        return ""
    q = quote(symbol)
    tick = q.get("tick") or {}
    parts = [
        f"LIVE METATRADER DATA (do not treat as historical knowledge): symbol={symbol}",
        f"bid={tick.get('bid')} ask={tick.get('ask')} last={tick.get('last')} time={tick.get('time')}",
    ]
    if wants_indicator:
        b = bars(symbol, config()["timeframe"], 200).get("bars") or []
        closes = [float(x[4]) for x in b if len(x) >= 5]
        if closes:
            def sma(n):
                return sum(closes[-n:]) / n if len(closes) >= n else None
            parts.append(f"SMA20={sma(20)} SMA50={sma(50)}")
            if len(closes) >= 15:
                gains=[]; losses=[]
                for a,z in zip(closes[-15:-1], closes[-14:]):
                    d=z-a; gains.append(max(d,0)); losses.append(max(-d,0))
                ag=sum(gains)/14; al=sum(losses)/14
                rsi=100.0 if al == 0 else 100-(100/(1+(ag/al)))
                parts.append(f"RSI14={rsi}")
    return "\n".join(parts)
