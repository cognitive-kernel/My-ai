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

- پنل عملیات مدیریتی GUI اکنون معادل گرافیکی status/health/sessions/memory/tools/policies/learning/repairs/rollback/diagnostics را از Settings ارائه می‌کند.

- Unified Control Plane اکنون namespace catalog و فرم GUI مشترک برای ساخت/ویرایش رکوردهای no-code دارد؛ این مسیر برای مدیریت Agent/Tool/Memory/Research/Security/Scheduler/Execution/Integration/Observability/Database/Prompt/Policy/Evaluation طراحی شده است.
- Runtime executor به Configuration Registry متصل شد تا mode و output-limit از تنظیمات مرکزی خوانده شوند.

## مرحله بعد
مرحله بعد از اتمام implementation، اجرای تست، regression، integration، security و runtime verification است. موارد roadmap تا آن مرحله به‌صورت [ ] باقی می‌مانند.

### GUI/CLI parity completion pass — 2026-10-02
- Extended the unified admin CLI with configuration profiles, backup/restore, learning-source catalog operations, and capability inventory.
- Added Settings API and GUI controls for configuration profiles using the same control-plane persistence as CLI.
- Added profile/capability entries to the GUI Action Registry.
- Existing generic Control Plane GUI now supports record edit, enable/disable, and delete alongside CLI CRUD operations.
- No tests, pytest, CI, or regression verification were run in this pass by explicit project instruction.

- Control Plane GUI lifecycle was completed for record create/edit/enable/disable/delete and action start/status/update, including progress/result/error fields; the corresponding API and CLI lifecycle remain backed by the same persistence layer.
- Expanded GUI Action Registry coverage for configuration history, provider/model catalog, learning catalog, database policy, security roles and evaluation/regression.
- The Settings page now exposes the Control Plane action lifecycle without requiring direct endpoint or CLI usage.
- Coding remains intentionally separate from verification: no test execution was started in this pass.


## آخرین pass — تکمیل No-Code parity (بدون اجرای تست)
- Control Plane GUI اکنون مسیرهای CRUD، فعال/غیرفعال‌سازی، حذف و مدیریت lifecycle عملیات را پوشش می‌دهد.
- Registryهای Prompt، Policy و Tool از طریق API/GUI قابل مدیریت شدند.
- چرخه پیشنهاد/تأیید/رد Plugin به Control Plane، API و GUI متصل شد.
- CLI مدیریت منابع یادگیری به‌روزرسانی شد و محاسبه content hash نیز در آن در دسترس است.
- CLI مدیریت Prompt/Policy/Tool/Plugin با همان لایه persistent پروژه اضافه شد.
- GUI Action Registry برای Provider، Learning، Prompt، Policy، Plugin و Tool گسترش یافت.
- طبق دستور پروژه، در این pass هیچ تست، pytest، CI یا regression اجرا نشده است.
