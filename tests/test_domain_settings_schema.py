import pytest

pytestmark = pytest.mark.timeout(30)


def test_mt4_mt5_domain_settings_are_registered_and_typed():
    from my_ai.settings_store import SETTING_REGISTRY

    expected = {
        "domain.mt4mt5.enabled": "enum",
        "domain.mt4mt5.version": "enum",
        "domain.mt4mt5.install_path": "text",
        "domain.mt4mt5.library_name": "text",
        "domain.mt4mt5.library_path": "text",
        "domain.mt4mt5.api_version": "text",
        "domain.mt4mt5.account": "text",
        "domain.mt4mt5.password": "text",
        "domain.mt4mt5.server": "text",
        "domain.mt4mt5.timeframe": "enum",
        "domain.mt4mt5.tick_data": "enum",
        "domain.mt4mt5.indicators": "enum",
        "domain.mt4mt5.market_analysis": "enum",
        "domain.mt4mt5.trading": "enum",
    }
    for key, kind in expected.items():
        assert SETTING_REGISTRY[key]["type"] == kind

    assert SETTING_REGISTRY["domain.mt4mt5.version"]["choices"] == ["MT4", "MT5"]
    assert SETTING_REGISTRY["domain.mt4mt5.password"]["secret"] is True
