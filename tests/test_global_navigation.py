from pathlib import Path

from my_ai.settings_feature import _settings_document
from my_ai.ui_extensions import _image_page, _learning_page, _settings_section, _settings_sections


NAV_ID = 'id="myAiGlobalNav"'


def test_settings_form_has_global_navigation_at_top():
    html = _settings_document()
    assert NAV_ID in html
    assert html.index(NAV_ID) < html.index("<h1 id='settingsHeroTitle'>")
    assert 'href="/settings"' in html


def test_dedicated_pages_have_the_same_global_navigation():
    pages = (
        _image_page(),
        _learning_page(),
        _settings_sections(),
        _settings_section("github"),
    )
    for html in pages:
        assert html.count(NAV_ID) == 1
        assert 'href="/settings"' in html
        assert 'href="/help"' in html


def test_global_navigation_is_injected_into_auth_pages_too():
    from my_ai.ui_extensions import _inject_global

    for path in ("/login", "/register"):
        html = _inject_global("<html><body><h1>page</h1></body></html>", path)
        assert html.count(NAV_ID) == 1
        assert html.index(NAV_ID) < html.index("<h1>page</h1>")


def test_main_page_uses_dashboard_settings_target():
    index = Path("my_ai/static/index.html").read_text(encoding="utf-8")
    assert "href='/settings'" in index
    assert "href='/settings/sections'" not in index
