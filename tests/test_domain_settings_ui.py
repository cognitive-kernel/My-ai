import pytest

pytestmark = pytest.mark.timeout(30)


def test_domain_form_matches_reference_structure_and_controls():
    from my_ai.settings_feature import SETTINGS_HTML

    for marker in (
        "domainReference",
        "MT4/MT5",
        "تحلیل مالی",
        "صنعت و مهندسی",
        "طراحی و گرافیک",
        "سایر دامنه‌ها",
        "کد آداپتور و کتابخانه‌ها",
        "تست اتصال",
        "نمونه کد استفاده",
        "راهنمای استفاده",
        "انتخاب نسخه",
        "مسیر نصب",
        "شماره حساب",
        "رمز عبور",
        "سرور",
        "تایم‌فریم پیش‌فرض",
        "دریافت قیمت‌های لحظه‌ای",
        "اجرای اندیکاتورها",
        "تحلیل داده‌ها",
        "مدیریت معاملات",
        "ذخیره تنظیمات",
    ):
        assert marker in SETTINGS_HTML

    for field in (
        "dom_enabled", "dom_install_path", "dom_account", "dom_password",
        "dom_server", "dom_timeframe", "dom_library_name", "dom_library_path",
        "dom_api", "dom_tick", "dom_indicators", "dom_analysis", "dom_trading",
    ):
        assert f"id='{field}'" in SETTINGS_HTML
