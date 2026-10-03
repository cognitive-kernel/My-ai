import pytest

pytestmark = pytest.mark.timeout(30)


def test_global_menu_opens_graphical_settings_dashboard():
    from my_ai.ui_extensions import _nav

    nav = _nav("/")
    assert 'href="/settings"' in nav
    assert "تنظیمات" in nav
    assert 'href="/settings/sections"' not in nav
