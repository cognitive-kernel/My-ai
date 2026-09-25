# Scheduler و یادگیری خودکار

Scheduler workerهای مستقل یادگیری را در پس‌زمینه اجرا می‌کند.

## رفتار

- چند مسیر یادگیری می‌توانند مستقل از هم وجود داشته باشند.
- CPU/RAM قبل از اجرای مرحله بررسی می‌شود.
- خطاها با backoff دوباره امتحان می‌شوند.
- Stop با event کنترل‌شده انجام می‌شود.
- پس از تکمیل domain، review هفتگی ثبت می‌شود.
- Review هر ۷ روز منابع را بررسی می‌کند.
- اگر مطلب جدید پیدا شود، curriculum به‌روزرسانی و worker همان domain به‌صورت خودکار فعال می‌شود.
- توقف دستی یک domain، auto-learning آن domain را خاموش می‌کند تا کاربر با «ادامه» آن را دوباره فعال کند.

## API

```
POST /scheduler/start
GET  /scheduler/status
POST /scheduler/stop
POST /learning/{language}/stop
POST /learning/{language}/resume
```

## وضعیت‌های اصلی

`starting`، `running`، `retrying`، `stopping`، `idle` و `completed`.

داشبورد اصلی وضعیت هر مسیر را جداگانه نمایش می‌دهد.
