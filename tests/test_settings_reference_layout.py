import pytest

pytestmark = pytest.mark.timeout(30)


def test_settings_matches_reference_shell():
    from my_ai.settings_feature import SETTINGS_HTML

    for marker in (
        "settingsApp",
        "settingsSidebar",
        "settingsTop",
        "settingsSearch",
        "settingsHero",
        "settingsTabs",
        "settingsSections",
        "settings-primary",
        "settings-secondary",
        "grid-template-columns:minmax(0,1.06fr) minmax(320px,.94fr)",
    ):
        assert marker in SETTINGS_HTML

    for label in (
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
        assert label in SETTINGS_HTML


def test_settings_keeps_all_existing_management_capabilities():
    from my_ai.settings_feature import SETTINGS_HTML

    for heading in (
        "مدیریت Provider و Model",
        "Routing و Fallback مدل",
        "منابع یادگیری و Evidence",
        "پشتیبان‌گیری و بازیابی",
        "مدیریت Migration",
        "مرکز مدیریت بدون کدنویسی",
        "داشبورد ماژول‌ها · فرم‌های گرافیکی ماژول‌ها",
        "Registryهای Agent و Plugin",
        "مدیریت کاربران",
        "مجوز ابزار کاربران",
        "ساخت آموزش جدید",
        "تولید تصویر کاملاً آفلاین",
        "لاگ‌های کنسول",
        "گزینه‌های تکمیل‌شده نقشه توسعه",
        "پروفایل‌های پیکربندی",
    ):
        assert heading in SETTINGS_HTML


def test_settings_reference_navigation_has_working_search_and_tabs():
    from my_ai.settings_feature import SETTINGS_HTML

    assert "search.addEventListener('input'" in SETTINGS_HTML
    assert "buildTabs(items)" in SETTINGS_HTML
    assert "showCategory('general')" in SETTINGS_HTML
    assert "settingsNav button" in SETTINGS_HTML
    assert "settings-primary" in SETTINGS_HTML
    assert "settings-secondary" in SETTINGS_HTML
    assert "<div class='settingsDashboard'" not in SETTINGS_HTML


def test_settings_all_current_sections_are_named_in_reference_ui():
    from my_ai.settings_feature import SETTINGS_HTML

    for heading in (
        "مدیریت Provider و Model",
        "Routing و Fallback مدل",
        "منابع یادگیری و Evidence",
        "پشتیبان‌گیری و بازیابی",
        "مدیریت Migration",
        "مرکز مدیریت بدون کدنویسی",
        "اتصال GitHub",
        "Self-Update",
        "Self-Repair",
        "یادگیری سریع",
        "تولید تصویر کاملاً آفلاین",
        "لاگ‌های کنسول",
        "منابع سخت‌افزاری",
        "Configuration Registry",
        "مرکز عملیات گرافیکی",
        "پنل عملیات مدیریتی",
        "پروفایل‌های پیکربندی",
        "گزینه‌های تکمیل‌شده نقشه توسعه",
        "داشبورد ماژول‌ها · فرم‌های گرافیکی ماژول‌ها",
        "مدیریت یکپارچه No-Code",
        "Registryهای Agent و Plugin",
        "مدیریت کاربران",
        "مجوز ابزار کاربران",
        "افزودن Topic به آموزش موجود",
        "ساخت آموزش جدید",
        "درباره My-AI",
    ):
        assert heading in SETTINGS_HTML
