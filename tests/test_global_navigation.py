from my_ai.settings_feature import _settings_document
from my_ai.ui_extensions import _image_page, _learning_page, _settings_section, _settings_sections


NAV_ID = 'id="myAiGlobalNav"'


def test_settings_form_has_global_navigation_at_top():
    html = _settings_document()
    assert NAV_ID in html
    assert html.index(NAV_ID) < html.index("<h1>تنظیمات My-AI</h1>")
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
