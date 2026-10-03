import json
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.timeout(30)


def test_mt4_connector_reads_real_bridge_tick(monkeypatch, tmp_path):
    from my_ai.domain import mt4

    bridge = tmp_path / "MQL4" / "Files"
    bridge.mkdir(parents=True)
    payload = {
        "symbol": "AUDUSD",
        "bid": 0.69541,
        "ask": 0.69552,
        "timestamp": time.time(),
        "account": "12345",
        "server": "Demo-Server",
    }
    (bridge / "my_ai_tick.json").write_text(json.dumps(payload), encoding="utf-8")

    values = {
        "domain.mt4mt5.enabled": True,
        "domain.mt4mt5.install_path": str(tmp_path),
        "domain.mt4mt5.library_path": "",
        "domain.mt4mt5.bridge_file": "MQL4/Files/my_ai_tick.json",
        "domain.mt4mt5.max_tick_age_seconds": 10,
        "domain.mt4mt5.account": "12345",
        "domain.mt4mt5.server": "Demo-Server",
    }
    monkeypatch.setattr(mt4, "get_bool", lambda key, default=False: bool(values.get(key, default)))
    monkeypatch.setattr(mt4, "get_setting", lambda key, default=None: values.get(key, default))

    quote = mt4.quote("AUD/USD")
    assert quote["source"] == "mt4"
    assert quote["bid"] == pytest.approx(0.69541)
    assert quote["ask"] == pytest.approx(0.69552)
    assert quote["account"] == "12345"


def test_mt4_connector_rejects_stale_tick(monkeypatch, tmp_path):
    from my_ai.domain import mt4

    bridge = tmp_path / "MQL4" / "Files"
    bridge.mkdir(parents=True)
    payload = {"symbol": "AUDUSD", "bid": 0.69, "ask": 0.70, "timestamp": time.time() - 60}
    (bridge / "my_ai_tick.json").write_text(json.dumps(payload), encoding="utf-8")
    values = {
        "domain.mt4mt5.enabled": True,
        "domain.mt4mt5.install_path": str(tmp_path),
        "domain.mt4mt5.library_path": "",
        "domain.mt4mt5.bridge_file": "MQL4/Files/my_ai_tick.json",
        "domain.mt4mt5.max_tick_age_seconds": 10,
    }
    monkeypatch.setattr(mt4, "get_bool", lambda key, default=False: bool(values.get(key, default)))
    monkeypatch.setattr(mt4, "get_setting", lambda key, default=None: values.get(key, default))

    with pytest.raises(mt4.MT4Unavailable, match="stale"):
        mt4.quote("AUDUSD")
