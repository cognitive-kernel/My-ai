from pathlib import Path

from my_ai import settings_feature as sf


def test_settings_page_contains_unified_module_gui():
    source = Path(sf.__file__).read_text(encoding="utf-8")
    assert "داشبورد گرافیکی ماژول‌ها" in source
    assert 'id=\'module-gui-list\'' in source


def test_module_gui_script_uses_control_plane_routes():
    source = Path(Path(sf.__file__).with_name("settings_script.js")).read_text(encoding="utf-8")
    assert "/settings/control-plane/namespaces" in source
    assert "/settings/control-plane?namespace=" in source
    assert "payload:payload" in source
