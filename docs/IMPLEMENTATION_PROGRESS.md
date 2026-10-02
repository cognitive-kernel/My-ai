# وضعیت پیاده‌سازی کدنویسی نقشه جامع

این سند مخصوص مرحله پیاده‌سازی است و با مرحله تست/Regression جداست.

## اصل اجرا
- هر قابلیت مدیریتی باید هم از GUI و هم از CLI قابل دسترسی باشد.
- GUI و CLI باید از یک persistence/control-plane مشترک استفاده کنند.
- secretها در مسیرهای مدیریتی به‌صورت plaintext نمایش داده نمی‌شوند.
- قابلیت‌های حساس باید permission و audit داشته باشند.
- تا قبل از شروع مرحله verification، موارد roadmap به‌عنوان «تکمیل تست‌شده» علامت نمی‌خورند.

## زیرساخت‌های پیاده‌سازی‌شده در این مرحله
- Configuration Registry توسعه‌یافته و versioned
- Unified Control Plane و lifecycle عملیات
- GUI Control Plane در Settings
- CLIهای scripts/myai_control.py و scripts/myai_admin.py
- Provider/Model Catalog، health، lifecycle و multi-key rotation
- Model routing و capability-aware selection
- Learning Source Catalog با approval/provenance/version
- Prompt/Policy/Tool Registry
- Security policy catalogs
- Database backup/restore API و GUI
- Configuration profiles
- Event-to-action runtime
- No-code workflow runtime
- Advanced Agent primitives شامل Skill، Knowledge Graph، Hybrid Retrieval، Context Planning، Verification/Confidence، Evaluation، Research، Secure Environment، Parallel Execution، Cache، Budget، Event، Meta-Agent و Agent OS
- Version-aware knowledge/experience evolution
- Regression intelligence
- Multimodal/Execution/Integration catalogs
- Plugin registry با approval gate
- Hard-coded configuration inventory

## تکمیل‌های اخیر در لایه مدیریت بدون کدنویسی
- Provider Catalog اکنون ویرایش مستقیم یک Provider موجود را با شناسه پشتیبانی می‌کند.
- GUI برای Provider شامل ویرایش، افزودن کلید و rotation کلید فعال شده است.
- CLI ادمین عملیات record CRUD، enable/disable، lifecycle action، provider/model CRUD و multi-key rotation را با همان persistence فراهم می‌کند.
- CLI برای Configuration Registry عملیات set/reset/import/export و مشاهده history دارد.
- Configuration Registry اکنون history تغییرات را در DB ثبت می‌کند و API تاریخچه نیز در Settings ارائه شده است.
- GUI و CLI همچنان از یک Control Plane/Registry مشترک استفاده می‌کنند.

## مرحله بعد
مرحله بعد از اتمام implementation، اجرای تست، regression، integration، security و runtime verification است. موارد roadmap تا آن مرحله به‌صورت [ ] باقی می‌مانند.
