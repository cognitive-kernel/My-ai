import pytest

pytestmark = pytest.mark.timeout(30)


def test_settings_reference_shell_is_the_dashboard():
    from my_ai.settings_feature import SETTINGS_HTML

    for marker in (
        "settingsApp",
        "settingsSidebar",
        "settingsTop",
        "settingsSearch",
        "settingsHero",
        "settingsTabs",
        "settingsToolbar",
    ):
        assert marker in SETTINGS_HTML

    assert "<div class='settingsDashboard'" not in SETTINGS_HTML
    assert "settingsTileGrid" not in SETTINGS_HTML


def test_settings_reference_sidebar_contains_all_categories():
    from my_ai.settings_feature import SETTINGS_HTML

    for title in (
        "عمومی",
        "مدیریت مدل‌ها",
        "پایگاه‌های داده",
        "اتصالات و API ها",
        "امنیت و مجوزها",
        "قالب‌های پاسخ",
        "ماژول‌ها و قابلیت‌ها",
        "قابلیت‌های دامنه خاص",
        "توسعه و برنامه‌نویسی",
        "ذخیره‌سازی و فایل‌ها",
        "لاگ‌ها و نظارت",
        "پشتیبان‌گیری",
        "درباره",
    ):
        assert title in SETTINGS_HTML


def test_settings_reference_keeps_module_and_roadmap_forms_reachable():
    from my_ai.settings_feature import SETTINGS_HTML

    assert "داشبورد ماژول‌ها · فرم‌های گرافیکی ماژول‌ها" in SETTINGS_HTML
    assert "گزینه‌های تکمیل‌شده نقشه توسعه" in SETTINGS_HTML
    assert "مرکز مدیریت بدون کدنویسی" in SETTINGS_HTML
    assert "پروفایل‌های پیکربندی" in SETTINGS_HTML
