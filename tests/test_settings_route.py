import pytest

pytestmark = pytest.mark.timeout(30)


def test_legacy_settings_sections_route_redirects_to_graphical_dashboard():
    from my_ai.ui_extensions import install_ui_extensions
    import inspect

    source = inspect.getsource(install_ui_extensions)
    assert "RedirectResponse(url='/settings', status_code=307)" in source


def test_main_menu_and_legacy_route_target_graphical_settings():
    from my_ai.ui_extensions import _nav
    nav = _nav("/settings")
    assert 'href="/settings"' in nav
