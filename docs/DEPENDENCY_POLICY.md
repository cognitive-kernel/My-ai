# سیاست مدیریت وابستگی‌ها

- منبع حقیقت وابستگی‌های runtime: `pyproject.toml`.
- فایل `requirements.lock` باید برای تمام وابستگی‌های runtime نسخه pin شده داشته باشد.
- هر تغییر dependency باید همزمان lock را به‌روزرسانی کند.
- CI باید بعد از تغییر dependencyها `pip-audit`، تست‌ها، lint/type/security checks، Docker build و compose config را اجرا کند.
- به‌روزرسانی dependency بدون بررسی changelog و اثر سازگاری پذیرفته نیست.
- dependency جدید باید دلیل استفاده و محل مصرف مشخص داشته باشد.
- dependencyهای بلااستفاده باید حذف شوند.
- نسخه‌های دارای آسیب‌پذیری غیرقابل‌قبول تا زمان رفع یا جایگزینی نباید وارد lock شوند.
- تغییرات dependency باید در commit جدا یا قابل ردیابی ثبت شوند.
