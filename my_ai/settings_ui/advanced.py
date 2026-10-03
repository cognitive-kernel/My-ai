from .shell import shell

def advanced() -> str:
    body = """<h1>تنظیمات پیشرفته</h1><p class='muted'>عملیات مدیریتی در صفحات مستقل انجام می‌شوند.</p>
<div class='grid'>
<section class='card'><h2>Registry</h2><p>مشاهده و تغییر تنظیمات ثبت‌شده.</p><a class='button' href='/settings/registry'>باز کردن Registry</a></section>
<section class='card'><h2>History</h2><p>تاریخچه تغییرات تنظیمات.</p><a class='button' href='/settings/registry/history'>باز کردن History</a></section>
<section class='card'><h2>Import / Export</h2><p>انتقال تنظیمات با کنترل دسترسی administrator.</p><a class='button' href='/settings/registry/export'>Export</a></section>
</div>"""
    return shell("تنظیمات پیشرفته", body)
