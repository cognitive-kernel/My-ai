import pytest

pytestmark = pytest.mark.timeout(30)


def test_settings_uses_graphical_dashboard_tiles():
    from my_ai.settings_feature import SETTINGS_HTML

    assert "settingsDashboard" in SETTINGS_HTML
    assert "settingsTileGrid" in SETTINGS_HTML
    for title in (
        "اتصال GitHub",
        "Self-Update",
        "Self-Repair",
        "منابع سیستم",
        "کاربران",
        "مجوزها",
        "یادگیری سریع",
        "آموزش‌های سفارشی",
        "ساخت تصویر",
        "لاگ‌ها",
    ):
        assert title in SETTINGS_HTML


def test_settings_dashboard_replaces_flat_settings_view():
    from my_ai.settings_feature import SETTINGS_HTML

    assert "showSettingsDashboard" in SETTINGS_HTML
    assert "settings-sections" in SETTINGS_HTML
    assert "settingsStandalone" in SETTINGS_HTML
    assert ".settingsSections{display:none}" in SETTINGS_HTML


def test_settings_dashboard_keeps_module_and_roadmap_forms_reachable():
    from my_ai.settings_feature import SETTINGS_HTML

    assert "data-settings-target='داشبورد ماژول‌ها · فرم‌های گرافیکی ماژول‌ها'" in SETTINGS_HTML
    assert "data-settings-target='گزینه‌های تکمیل‌شده نقشه توسعه'" in SETTINGS_HTML
