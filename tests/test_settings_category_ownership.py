import re
import pytest

pytestmark = pytest.mark.timeout(30)


def test_each_existing_settings_section_belongs_to_one_sidebar_category():
    from my_ai.settings_feature import SETTINGS_HTML

    titles = [
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
    ]
    meta = re.search(r"var meta=\{(.*?)\n  \};", SETTINGS_HTML, re.S).group(1)
    for title in titles:
        occurrences = len(re.findall(re.escape(title), meta))
        assert occurrences == 1, (title, occurrences)
