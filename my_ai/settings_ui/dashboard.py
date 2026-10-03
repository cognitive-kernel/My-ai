from html import escape
from .shell import shell

def index() -> str:
    cards = [
        ("MetaTrader 4/5", "اتصال، حساب، سرور، ترمینال، تست اتصال و داده بازار.", "/settings/ui/metatrader"),
        ("مدل و Provider", "Providerها، مدل‌ها و مسیر انتخاب مدل.", "/settings/providers"),
        ("یادگیری", "دوره‌ها، منابع و زمان‌بندی یادگیری.", "/learning"),
        ("امنیت", "Policy، نقش‌ها و مجوزهای ابزار.", "/settings/security-policies"),
        ("GitHub", "اتصال GitHub و تنظیمات repository.", "/settings/ui/github"),
        ("منابع سیستم", "CPU، RAM و تنظیمات اجرای مدل.", "/settings/ui/resources"),
        ("لاگ و مشاهده‌پذیری", "سطح لاگ و وضعیت مشاهده‌پذیری.", "/settings/ui/observability"),
        ("تنظیمات پیشرفته", "Registry، تاریخچه، import/export و کنترل‌های مدیریتی.", "/settings/ui/advanced"),
    ]
    body = "<h1>تنظیمات</h1><p class='muted'>هر حوزه یک فرم مستقل دارد؛ هر فرم فقط مسئول همان bounded context است.</p><div class='grid'>"
    body += "".join(f"<section class='card'><h2>{escape(t)}</h2><p>{escape(d)}</p><a class='button' href='{h}'>باز کردن</a></section>" for t,d,h in cards)
    body += "</div>"
    return shell("تنظیمات", body)
