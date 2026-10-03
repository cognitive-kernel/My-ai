from pathlib import Path

import pytest

pytestmark = pytest.mark.timeout(30)


def test_mt4_settings_are_persisted_and_connection_test_is_runtime_based():
    source = Path("my_ai/settings_feature.py").read_text(encoding="utf-8")
    assert '@router.get("/settings/domain-capabilities")' in source
    assert '@router.put("/settings/domain-capabilities")' in source
    assert '@router.post("/settings/domain-capabilities/test")' in source
    assert 'set_setting("mt4.install_path"' in source
    assert 'from .domain.mt4 import status' in source


def test_domain_settings_loads_legacy_mt4_namespace(monkeypatch):
    from my_ai import settings_feature

    values = {
        "mt4.enabled": "true",
        "mt4.version": "MT4",
        "mt4.install_path": r"C:\MT4",
        "mt4.library_name": "mt4.dll",
        "mt4.library_path": r"C:\MT4\Libraries",
        "mt4.api_version": "v2",
        "mt4.account": "123456",
        "mt4.password": "secret",
        "mt4.server": "Broker-Server",
        "mt4.timeframe": "H1",
        "mt4.tick_data": "true",
        "mt4.indicators": "false",
        "mt4.market_analysis": "true",
        "mt4.trading": "false",
    }
    monkeypatch.setattr(settings_feature, "get_setting", lambda key, default=None: values.get(key, default))
    data = settings_feature._domain_settings()
    assert data["install_path"] == r"C:\MT4"
    assert data["library_path"] == r"C:\MT4\Libraries"
    assert data["account"] == "123456"
    assert data["server"] == "Broker-Server"
    assert data["timeframe"] == "H1"
    assert data["indicators"] is False
    assert data["trading"] is False
