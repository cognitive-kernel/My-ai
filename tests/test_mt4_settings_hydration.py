from pathlib import Path

def test_mt4_settings_are_hydrated_from_saved_endpoint():
    source = Path("my_ai/settings_feature.py").read_text(encoding="utf-8")
    script = Path("my_ai/settings_script.js").read_text(encoding="utf-8")
    assert 'function loadDomainSettings(){' in source
    assert "req('/settings/domain-capabilities')" in source
    for field in (
        "dom_enabled", "dom_install_path", "dom_library_name", "dom_library_path",
        "dom_api", "dom_account", "dom_password", "dom_server", "dom_timeframe",
        "dom_tick", "dom_indicators", "dom_analysis", "dom_trading",
    ):
        assert f"getElementById('{field}')" in source
    assert 'setTimeout(refreshDomainSettingsAfterBootstrap,0);' in script
    assert 'async function hydratePersistedSettings()' in script


def test_mt4_saved_namespace_fallback_is_present():
    source = Path("my_ai/settings_feature.py").read_text(encoding="utf-8")
    for key in (
        "domain.mt4mt5.install_path", "domain.mt4.install_path", "mt4.install_path",
        "domain.mt4mt5.library_path", "domain.mt4.library_path", "mt4.library_path",
        "domain.mt4mt5.server", "domain.mt4.server", "mt4.server",
    ):
        assert key in source
