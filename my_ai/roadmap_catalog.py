"""Roadmap-backed no-code settings catalog.

Generated from the checked items in docs/نقشه جامع توسعه و مدیریت بدون کدنویسی.md.
The entries are intentionally read-only: a roadmap completion is a capability/status,
not an arbitrary feature toggle.
"""
from __future__ import annotations

ROADMAP_OPTIONS = [
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "هر رفتار قابل تغییر پروژه باید یک configuration key/versioned داشته باشد."
    },
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "هر configuration قابل مشاهده و ویرایش از Settings باشد."
    },
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "تنظیمات در DB پایدار ذخیره شوند و بعد از restart حفظ شوند."
    },
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "تغییر setting بدون تغییر source code اثر کند."
    },
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "برای هر setting نوع، default، range، validation، توضیح و dependency مشخص باشد."
    },
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "secretها جداگانه و رمزنگاری‌شده ذخیره شوند."
    },
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "تغییرات configuration audit شوند."
    },
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "امکان reset هر setting به default وجود داشته باشد."
    },
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "امکان export/import تنظیمات وجود داشته باشد."
    },
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "configuration versioning و migration وجود داشته باشد."
    },
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "تغییر settingهای حساس نیازمند authorization مناسب باشد."
    },
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "settings schema از کد business جدا باشد."
    },
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "هیچ setting مهمی فقط در `.env` یا constant کد باقی نماند."
    },
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "یک Configuration Registry مرکزی برای تمام moduleها ایجاد شود."
    },
    {
        "section": "0. اصل معماری جدید — Configuration First / No-Code",
        "title": "UI به‌صورت schema-driven از Registry فرم بسازد تا افزودن setting جدید نیازمند ساخت دستی فرم نباشد."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "انتخاب provider از configuration موجود."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "تنظیم Ollama base URL/model از configuration."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "تنظیم OpenAI-compatible base URL/model/API key از configuration."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "retry/timeout/backoff قابل تنظیم در runtime."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "fallback model موجود."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "فرم «افزودن Provider» با نام، نوع، endpoint، authentication، timeout و capabilities."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "فرم «افزودن Model» با provider، model ID، taskها، context، limits و priority."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "حذف/ویرایش/فعال/غیرفعال کردن provider و model بدون کدنویسی."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "تعریف چند API key برای یک provider و rotation آنها."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "تعریف fallback chain از UI."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "تعریف routing rule برای chat/coding/reasoning/embedding از UI."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "health-check و test connection از UI برای هر provider/model."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "انتخاب خودکار model بر اساس capability، هزینه، latency و availability از UI."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "ثبت و مشاهده مصرف، latency، خطا و fallback هر model."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "import/export catalog مدل‌ها."
    },
    {
        "section": "1. LLM / Model Management",
        "title": "حذف وابستگی routing به model nameهای hard-coded."
    },
    {
        "section": "1.1 اتصال LLM اختصاصی / Custom LLM Provider",
        "title": "مسیر Provider برای LLM سفارشیِ OpenAI-compatible در runtime ایجاد شود."
    },
    {
        "section": "1.1 اتصال LLM اختصاصی / Custom LLM Provider",
        "title": "endpoint، model ID و API key مربوط به LLM سفارشی از Configuration Registry قابل تنظیم باشند."
    },
    {
        "section": "1.1 اتصال LLM اختصاصی / Custom LLM Provider",
        "title": "انتخاب Provider فعال از Configuration Registry انجام شود."
    },
    {
        "section": "1.1 اتصال LLM اختصاصی / Custom LLM Provider",
        "title": "برای LLMهای دارای API غیر OpenAI-compatible یک Provider Adapter عمومی وجود داشته باشد."
    },
    {
        "section": "1.1 اتصال LLM اختصاصی / Custom LLM Provider",
        "title": "تعریف Provider سفارشی از UI با تست اتصال، capabilities، health-check و version ثبت شود."
    },
    {
        "section": "1.1 اتصال LLM اختصاصی / Custom LLM Provider",
        "title": "مدل سفارشی در Model Catalog با capability و نسخه ثبت شود."
    },
    {
        "section": "1.1 اتصال LLM اختصاصی / Custom LLM Provider",
        "title": "مهاجرت از یک Provider به LLM اختصاصی بدون تغییر workflow و Agent تضمین شود."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "ایجاد Course از Settings."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "افزودن Topic دستی."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "تعیین هدف و source URL برای Topic."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "اجرای یادگیری Course."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "کشف منابع وب در review خودکار."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "فرم «آموزش جدید» با دو حالت `Auto Discover` و `Manual Sources`."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "امکان معرفی یک یا چند URL، فایل، کتاب، مستندات یا repository به‌صورت دستی."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "امکان درخواست «خودت مرجع معتبر پیدا کن» برای هر Topic."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "انتخاب نوع منابع مجاز: official docs / university / standards / GitHub / books / custom."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "تعیین اولویت و وزن منابع."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "امکان تأیید یا رد منابع کشف‌شده قبل از یادگیری."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "امکان اضافه/حذف/ویرایش منبع بعد از ایجاد Course."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "استخراج خودکار curriculum از یک مرجع یا مجموعه منابع."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "تشخیص تغییرات منبع و trigger کردن relearning."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "امکان pause/resume/reset یک Topic از UI."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "مشاهده evidence و provenance هر lesson."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "تعیین LLM مورد استفاده برای هر Course/Topic از UI."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "تعیین schedule یادگیری و مرور از UI."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "تعیین معیار mastery و حداقل score از UI."
    },
    {
        "section": "2. Learning / آموزش",
        "title": "تعیین سیاست «منبع دستی اولویت دارد» یا «ترکیبی» از UI."
    },
    {
        "section": "3. Agent Runtime",
        "title": "تنظیم system behavior بدون تغییر کد."
    },
    {
        "section": "3. Agent Runtime",
        "title": "مدیریت promptهای اصلی از UI با versioning."
    },
    {
        "section": "3. Agent Runtime",
        "title": "مدیریت persona/role از UI."
    },
    {
        "section": "3. Agent Runtime",
        "title": "مدیریت planning strategy از UI."
    },
    {
        "section": "3. Agent Runtime",
        "title": "تعیین maximum steps/iterations از UI."
    },
    {
        "section": "3. Agent Runtime",
        "title": "تعیین timeout هر execution از UI."
    },
    {
        "section": "3. Agent Runtime",
        "title": "تعیین سیاست توقف/لغو از UI."
    },
    {
        "section": "3. Agent Runtime",
        "title": "تعیین مدل مناسب هر نوع task از UI."
    },
    {
        "section": "3. Agent Runtime",
        "title": "تعریف workflowهای Agent از UI."
    },
    {
        "section": "3. Agent Runtime",
        "title": "امکان ساخت workflow جدید بدون کدنویسی."
    },
    {
        "section": "3. Agent Runtime",
        "title": "امکان فعال/غیرفعال کردن stageهای workflow."
    },
    {
        "section": "3. Agent Runtime",
        "title": "مشاهده trace کامل execution."
    },
    {
        "section": "4. Tools / Tool Runtime",
        "title": "catalog مرکزی ابزارها."
    },
    {
        "section": "4. Tools / Tool Runtime",
        "title": "افزودن Tool از UI با name، description، input schema و output schema."
    },
    {
        "section": "4. Tools / Tool Runtime",
        "title": "فعال/غیرفعال کردن Tool از UI."
    },
    {
        "section": "4. Tools / Tool Runtime",
        "title": "تنظیم permission هر Tool از UI."
    },
    {
        "section": "4. Tools / Tool Runtime",
        "title": "تنظیم timeout/retry هر Tool از UI."
    },
    {
        "section": "4. Tools / Tool Runtime",
        "title": "تعیین اینکه Tool در چه taskهایی قابل استفاده است."
    },
    {
        "section": "4. Tools / Tool Runtime",
        "title": "تعریف Toolهای HTTP/API بدون تغییر کد."
    },
    {
        "section": "4. Tools / Tool Runtime",
        "title": "تعریف webhook/integration بدون تغییر کد."
    },
    {
        "section": "4. Tools / Tool Runtime",
        "title": "تعریف command/subprocess Tool با sandbox policy."
    },
    {
        "section": "4. Tools / Tool Runtime",
        "title": "versioning ابزارها."
    },
    {
        "section": "4. Tools / Tool Runtime",
        "title": "health-check ابزارها."
    },
    {
        "section": "4. Tools / Tool Runtime",
        "title": "مشاهده مصرف و خطاهای ابزارها."
    },
    {
        "section": "4. Tools / Tool Runtime",
        "title": "جلوگیری از Toolهای ناشناخته یا بدون policy."
    },
    {
        "section": "5. Memory / Knowledge",
        "title": "انتخاب memory backend از UI."
    },
    {
        "section": "5. Memory / Knowledge",
        "title": "تنظیم retention از UI."
    },
    {
        "section": "5. Memory / Knowledge",
        "title": "تنظیم embedding model از UI."
    },
    {
        "section": "5. Memory / Knowledge",
        "title": "تنظیم duplicate threshold از UI."
    },
    {
        "section": "5. Memory / Knowledge",
        "title": "تنظیم chunking/indexing از UI."
    },
    {
        "section": "5. Memory / Knowledge",
        "title": "مشاهده، ویرایش و حذف memory از UI."
    },
    {
        "section": "5. Memory / Knowledge",
        "title": "import/export knowledge."
    },
    {
        "section": "5. Memory / Knowledge",
        "title": "مدیریت source/provenance هر knowledge item."
    },
    {
        "section": "5. Memory / Knowledge",
        "title": "policy جدا برای short-term، long-term و experiential memory."
    },
    {
        "section": "5. Memory / Knowledge",
        "title": "تعیین اینکه چه نوع اطلاعاتی وارد memory شود."
    },
    {
        "section": "5. Memory / Knowledge",
        "title": "امکان پاک‌سازی selective memory بدون کدنویسی."
    },
    {
        "section": "6. Web Learning / Research",
        "title": "تعریف search provider از UI."
    },
    {
        "section": "6. Web Learning / Research",
        "title": "افزودن/حذف search provider."
    },
    {
        "section": "6. Web Learning / Research",
        "title": "تنظیم domain allowlist/denylist از UI."
    },
    {
        "section": "6. Web Learning / Research",
        "title": "تنظیم source ranking از UI."
    },
    {
        "section": "6. Web Learning / Research",
        "title": "تعیین منابع معتبر برای هر موضوع."
    },
    {
        "section": "6. Web Learning / Research",
        "title": "تنظیم timeout و max content از UI."
    },
    {
        "section": "6. Web Learning / Research",
        "title": "تعریف crawling/fetch policy از UI."
    },
    {
        "section": "6. Web Learning / Research",
        "title": "امکان افزودن source دستی."
    },
    {
        "section": "6. Web Learning / Research",
        "title": "امکان تأیید source قبل از ذخیره knowledge."
    },
    {
        "section": "6. Web Learning / Research",
        "title": "ثبت provenance کامل."
    },
    {
        "section": "7. Security / Policy / Authorization",
        "title": "permissionهای Tool از Settings موجود است."
    },
    {
        "section": "7. Security / Policy / Authorization",
        "title": "Policy Engine کاملاً schema-driven شود."
    },
    {
        "section": "7. Security / Policy / Authorization",
        "title": "تعریف role از UI."
    },
    {
        "section": "7. Security / Policy / Authorization",
        "title": "تعریف capability از UI."
    },
    {
        "section": "7. Security / Policy / Authorization",
        "title": "تعیین read/write/execute برای هر role/user/tool از UI."
    },
    {
        "section": "7. Security / Policy / Authorization",
        "title": "تنظیم network policy از UI."
    },
    {
        "section": "7. Security / Policy / Authorization",
        "title": "تنظیم filesystem policy از UI."
    },
    {
        "section": "7. Security / Policy / Authorization",
        "title": "تنظیم subprocess policy از UI."
    },
    {
        "section": "7. Security / Policy / Authorization",
        "title": "تنظیم self-modification policy از UI."
    },
    {
        "section": "7. Security / Policy / Authorization",
        "title": "تعریف approval requirement برای عملیات حساس از UI."
    },
    {
        "section": "7. Security / Policy / Authorization",
        "title": "مشاهده audit trail از UI."
    },
    {
        "section": "7. Security / Policy / Authorization",
        "title": "export policy."
    },
    {
        "section": "7. Security / Policy / Authorization",
        "title": "versioning policy."
    },
    {
        "section": "8. Self-Update / Self-Repair / Self-Improvement",
        "title": "approval، health URL و enable/disable در Settings وجود دارد."
    },
    {
        "section": "8. Self-Update / Self-Repair / Self-Improvement",
        "title": "تنظیم کامل چرخه self-update از UI."
    },
    {
        "section": "8. Self-Update / Self-Repair / Self-Improvement",
        "title": "تنظیم candidate test policy از UI."
    },
    {
        "section": "8. Self-Update / Self-Repair / Self-Improvement",
        "title": "تنظیم snapshot policy از UI."
    },
    {
        "section": "8. Self-Update / Self-Repair / Self-Improvement",
        "title": "تنظیم rollback policy از UI."
    },
    {
        "section": "8. Self-Update / Self-Repair / Self-Improvement",
        "title": "تعیین اینکه چه فایل/مسیرهایی قابل mutation هستند."
    },
    {
        "section": "8. Self-Update / Self-Repair / Self-Improvement",
        "title": "تعیین اینکه چه تغییراتی نیازمند approval دستی هستند."
    },
    {
        "section": "8. Self-Update / Self-Repair / Self-Improvement",
        "title": "مشاهده proposal/diff از UI."
    },
    {
        "section": "8. Self-Update / Self-Repair / Self-Improvement",
        "title": "approve/reject proposal از UI."
    },
    {
        "section": "8. Self-Update / Self-Repair / Self-Improvement",
        "title": "مشاهده health check و rollback history از UI."
    },
    {
        "section": "8. Self-Update / Self-Repair / Self-Improvement",
        "title": "تنظیم lesson/failure policy از UI."
    },
    {
        "section": "9. Scheduler / Resources",
        "title": "CPU/RAM/thread/GPU settings موجود است."
    },
    {
        "section": "9. Scheduler / Resources",
        "title": "scheduler interval از UI."
    },
    {
        "section": "9. Scheduler / Resources",
        "title": "worker count از UI."
    },
    {
        "section": "9. Scheduler / Resources",
        "title": "concurrency از UI."
    },
    {
        "section": "9. Scheduler / Resources",
        "title": "retry/backoff از UI."
    },
    {
        "section": "9. Scheduler / Resources",
        "title": "priority هر job از UI."
    },
    {
        "section": "9. Scheduler / Resources",
        "title": "schedule هر learning/review job از UI."
    },
    {
        "section": "9. Scheduler / Resources",
        "title": "pause/resume/cancel job از UI."
    },
    {
        "section": "9. Scheduler / Resources",
        "title": "resource profileهای قابل انتخاب."
    },
    {
        "section": "9. Scheduler / Resources",
        "title": "مشاهده queue و worker state از UI."
    },
    {
        "section": "9. Scheduler / Resources",
        "title": "تعریف quota برای user/task از UI."
    },
    {
        "section": "10. Image / Voice / Multimodal",
        "title": "تنظیمات Image موجود است."
    },
    {
        "section": "10. Image / Voice / Multimodal",
        "title": "افزودن provider تصویر از UI."
    },
    {
        "section": "10. Image / Voice / Multimodal",
        "title": "افزودن/حذف model تصویر از UI."
    },
    {
        "section": "10. Image / Voice / Multimodal",
        "title": "تنظیم provider/model صوت از UI."
    },
    {
        "section": "10. Image / Voice / Multimodal",
        "title": "تنظیم Whisper model/language از UI."
    },
    {
        "section": "10. Image / Voice / Multimodal",
        "title": "تنظیم TTS provider/model/voice از UI."
    },
    {
        "section": "10. Image / Voice / Multimodal",
        "title": "مدیریت multimodal routing از UI."
    },
    {
        "section": "10. Image / Voice / Multimodal",
        "title": "health-check providerهای multimodal."
    },
    {
        "section": "11. Execution / Code / Projects",
        "title": "تنظیم executor mode از UI."
    },
    {
        "section": "11. Execution / Code / Projects",
        "title": "تنظیم image/runtime executor از UI."
    },
    {
        "section": "11. Execution / Code / Projects",
        "title": "timeout/memory/CPU/PID/output limits از UI."
    },
    {
        "section": "11. Execution / Code / Projects",
        "title": "sandbox policy از UI."
    },
    {
        "section": "11. Execution / Code / Projects",
        "title": "project root از UI با validation امنیتی."
    },
    {
        "section": "11. Execution / Code / Projects",
        "title": "تعریف template پروژه از UI."
    },
    {
        "section": "11. Execution / Code / Projects",
        "title": "تعریف build/run commands از UI با policy."
    },
    {
        "section": "11. Execution / Code / Projects",
        "title": "مدیریت environment variables پروژه از UI با secret handling."
    },
    {
        "section": "11. Execution / Code / Projects",
        "title": "مشاهده execution history از UI."
    },
    {
        "section": "12. Git / GitHub / Integrations",
        "title": "GitHub endpoint/repository/username/token از Settings قابل تنظیم است."
    },
    {
        "section": "12. Git / GitHub / Integrations",
        "title": "افزودن integration جدید بدون کدنویسی."
    },
    {
        "section": "12. Git / GitHub / Integrations",
        "title": "تعریف credential از UI."
    },
    {
        "section": "12. Git / GitHub / Integrations",
        "title": "enable/disable integration."
    },
    {
        "section": "12. Git / GitHub / Integrations",
        "title": "test connection."
    },
    {
        "section": "12. Git / GitHub / Integrations",
        "title": "mapping event → action از UI."
    },
    {
        "section": "12. Git / GitHub / Integrations",
        "title": "webhook management از UI."
    },
    {
        "section": "12. Git / GitHub / Integrations",
        "title": "provider-specific configuration schema."
    },
    {
        "section": "13. API / Server / Deployment",
        "title": "host/port از Settings."
    },
    {
        "section": "13. API / Server / Deployment",
        "title": "CORS از Settings."
    },
    {
        "section": "13. API / Server / Deployment",
        "title": "session timeout از Settings."
    },
    {
        "section": "13. API / Server / Deployment",
        "title": "upload limits از Settings."
    },
    {
        "section": "13. API / Server / Deployment",
        "title": "request timeout از Settings."
    },
    {
        "section": "13. API / Server / Deployment",
        "title": "rate limit از Settings."
    },
    {
        "section": "13. API / Server / Deployment",
        "title": "feature flags از Settings."
    },
    {
        "section": "13. API / Server / Deployment",
        "title": "maintenance/read-only mode از Settings."
    },
    {
        "section": "13. API / Server / Deployment",
        "title": "health/readiness policy از Settings."
    },
    {
        "section": "13. API / Server / Deployment",
        "title": "notification/webhook configuration از Settings."
    },
    {
        "section": "14. Observability",
        "title": "log level از Settings قابل تنظیم است."
    },
    {
        "section": "14. Observability",
        "title": "log destinations از UI."
    },
    {
        "section": "14. Observability",
        "title": "metrics retention از UI."
    },
    {
        "section": "14. Observability",
        "title": "trace retention از UI."
    },
    {
        "section": "14. Observability",
        "title": "telemetry enable/disable از UI."
    },
    {
        "section": "14. Observability",
        "title": "alert rules از UI."
    },
    {
        "section": "14. Observability",
        "title": "notification destinations از UI."
    },
    {
        "section": "14. Observability",
        "title": "dashboard configuration از UI."
    },
    {
        "section": "14. Observability",
        "title": "export diagnostics از UI."
    },
    {
        "section": "15. Database / Backup / Migration",
        "title": "DB path از Settings."
    },
    {
        "section": "15. Database / Backup / Migration",
        "title": "backup schedule از Settings."
    },
    {
        "section": "15. Database / Backup / Migration",
        "title": "retention policy از Settings."
    },
    {
        "section": "15. Database / Backup / Migration",
        "title": "backup destination از UI."
    },
    {
        "section": "15. Database / Backup / Migration",
        "title": "encryption policy از UI."
    },
    {
        "section": "15. Database / Backup / Migration",
        "title": "restore از UI با confirmation و validation."
    },
    {
        "section": "15. Database / Backup / Migration",
        "title": "migration management از UI."
    },
    {
        "section": "15. Database / Backup / Migration",
        "title": "export/import schema-compatible."
    },
    {
        "section": "15. Database / Backup / Migration",
        "title": "مشاهده DB health/integrity از UI."
    },
    {
        "section": "16. Prompt / Policy / Behavior Registry",
        "title": "Prompt Registry مرکزی."
    },
    {
        "section": "16. Prompt / Policy / Behavior Registry",
        "title": "Policy Registry مرکزی."
    },
    {
        "section": "16. Prompt / Policy / Behavior Registry",
        "title": "نسخه‌بندی prompt/policy."
    },
    {
        "section": "16. Prompt / Policy / Behavior Registry",
        "title": "فعال‌سازی نسخه مشخص از UI."
    },
    {
        "section": "16. Prompt / Policy / Behavior Registry",
        "title": "rollback prompt/policy."
    },
    {
        "section": "16. Prompt / Policy / Behavior Registry",
        "title": "diff نسخه‌ها."
    },
    {
        "section": "16. Prompt / Policy / Behavior Registry",
        "title": "تست prompt قبل از فعال‌سازی."
    },
    {
        "section": "16. Prompt / Policy / Behavior Registry",
        "title": "تعیین prompt/model بر اساس task."
    },
    {
        "section": "17. Configuration Registry — زیرساخت لازم",
        "title": "تعریف schema واحد برای همه settings."
    },
    {
        "section": "17. Configuration Registry — زیرساخت لازم",
        "title": "registry شامل key/type/default/validation/secret/category/description."
    },
    {
        "section": "17. Configuration Registry — زیرساخت لازم",
        "title": "UI فرم‌ها را از registry تولید کند."
    },
    {
        "section": "17. Configuration Registry — زیرساخت لازم",
        "title": "API generic برای GET/PUT/DELETE settings."
    },
    {
        "section": "17. Configuration Registry — زیرساخت لازم",
        "title": "dependency بین settings."
    },
    {
        "section": "17. Configuration Registry — زیرساخت لازم",
        "title": "validation server-side و client-side."
    },
    {
        "section": "17. Configuration Registry — زیرساخت لازم",
        "title": "migration برای تغییر schema."
    },
    {
        "section": "17. Configuration Registry — زیرساخت لازم",
        "title": "audit برای تغییرات."
    },
    {
        "section": "17. Configuration Registry — زیرساخت لازم",
        "title": "import/export configuration."
    },
    {
        "section": "17. Configuration Registry — زیرساخت لازم",
        "title": "reset-to-default."
    },
    {
        "section": "17. Configuration Registry — زیرساخت لازم",
        "title": "configuration profiles مثل Development / Production / Offline."
    },
    {
        "section": "18. Dynamic Plugin / Provider Architecture",
        "title": "Provider interface عمومی."
    },
    {
        "section": "18. Dynamic Plugin / Provider Architecture",
        "title": "ثبت provider از configuration."
    },
    {
        "section": "18. Dynamic Plugin / Provider Architecture",
        "title": "discovery providerهای نصب‌شده."
    },
    {
        "section": "18. Dynamic Plugin / Provider Architecture",
        "title": "enable/disable provider."
    },
    {
        "section": "18. Dynamic Plugin / Provider Architecture",
        "title": "capability declaration."
    },
    {
        "section": "18. Dynamic Plugin / Provider Architecture",
        "title": "health check."
    },
    {
        "section": "18. Dynamic Plugin / Provider Architecture",
        "title": "version compatibility."
    },
    {
        "section": "18. Dynamic Plugin / Provider Architecture",
        "title": "جلوگیری از import مستقیم providerهای hard-coded در business logic."
    },
    {
        "section": "19. User Experience — مدیریت بدون کدنویسی",
        "title": "Settings به دسته‌های واضح تقسیم شود."
    },
    {
        "section": "19. User Experience — مدیریت بدون کدنویسی",
        "title": "جست‌وجوی settings."
    },
    {
        "section": "19. User Experience — مدیریت بدون کدنویسی",
        "title": "نمایش «این setting روی چه چیزی اثر دارد؟»."
    },
    {
        "section": "19. User Experience — مدیریت بدون کدنویسی",
        "title": "نمایش مقدار فعلی/default."
    },
    {
        "section": "19. User Experience — مدیریت بدون کدنویسی",
        "title": "نمایش آخرین تغییر و تغییر‌دهنده."
    },
    {
        "section": "19. User Experience — مدیریت بدون کدنویسی",
        "title": "undo/reset."
    },
    {
        "section": "19. User Experience — مدیریت بدون کدنویسی",
        "title": "validation قبل از save."
    },
    {
        "section": "19. User Experience — مدیریت بدون کدنویسی",
        "title": "test connection / test configuration کنار هر integration."
    },
    {
        "section": "19. User Experience — مدیریت بدون کدنویسی",
        "title": "wizard برای عملیات پیچیده."
    },
    {
        "section": "19. User Experience — مدیریت بدون کدنویسی",
        "title": "import/export تنظیمات."
    },
    {
        "section": "19. User Experience — مدیریت بدون کدنویسی",
        "title": "نمایش dependency و warningهای مرتبط."
    },
    {
        "section": "19. User Experience — مدیریت بدون کدنویسی",
        "title": "قابلیت مدیریت پروژه برای کاربر غیر برنامه‌نویس."
    },
    {
        "section": "20. Hard-coded Audit — قانون نهایی",
        "title": "inventory تمام `os.getenv`ها و constants قابل تغییر."
    },
    {
        "section": "20. Hard-coded Audit — قانون نهایی",
        "title": "inventory تمام provider/model nameهای hard-coded."
    },
    {
        "section": "20. Hard-coded Audit — قانون نهایی",
        "title": "inventory تمام URLهای قابل تغییر."
    },
    {
        "section": "20. Hard-coded Audit — قانون نهایی",
        "title": "inventory تمام timeout/retry/limitهای قابل تغییر."
    },
    {
        "section": "20. Hard-coded Audit — قانون نهایی",
        "title": "inventory تمام feature flagهای hard-coded."
    },
    {
        "section": "20. Hard-coded Audit — قانون نهایی",
        "title": "inventory تمام policyهای hard-coded."
    },
    {
        "section": "20. Hard-coded Audit — قانون نهایی",
        "title": "inventory تمام مسیرهای filesystem قابل تغییر."
    },
    {
        "section": "20. Hard-coded Audit — قانون نهایی",
        "title": "inventory تمام scheduleها و intervalهای hard-coded."
    },
    {
        "section": "21. معماری Agent",
        "title": "Tool Runtime استاندارد: validate → authorize → execute → observe → audit."
    },
    {
        "section": "21. معماری Agent",
        "title": "Event Bus داخلی برای decoupling."
    },
    {
        "section": "21. معماری Agent",
        "title": "cancellation استاندارد."
    },
    {
        "section": "23. LLM Abstraction",
        "title": "Agent فقط به LLM interface وابسته باشد."
    },
    {
        "section": "23. LLM Abstraction",
        "title": "provider adapters مستقل باشند."
    },
    {
        "section": "23. LLM Abstraction",
        "title": "provider جدید بدون تغییر Agent قابل اضافه‌شدن باشد."
    },
    {
        "section": "23. LLM Abstraction",
        "title": "model capability registry."
    },
    {
        "section": "23. LLM Abstraction",
        "title": "provider/model lifecycle از Settings مدیریت شود."
    },
    {
        "section": "24. Learning Safety",
        "title": "محتوای وب مستقیماً به executable instruction تبدیل نشود."
    },
    {
        "section": "24. Learning Safety",
        "title": "source → extract → validate → normalize → store → evaluate → use."
    },
    {
        "section": "24. Learning Safety",
        "title": "provenance برای تمام learned knowledge."
    },
    {
        "section": "24. Learning Safety",
        "title": "امکان manual approval برای learning حساس."
    },
    {
        "section": "25. CLI / Admin Operations",
        "title": "status."
    },
    {
        "section": "25. CLI / Admin Operations",
        "title": "health."
    },
    {
        "section": "25. CLI / Admin Operations",
        "title": "sessions."
    },
    {
        "section": "25. CLI / Admin Operations",
        "title": "memory."
    },
    {
        "section": "25. CLI / Admin Operations",
        "title": "tools."
    },
    {
        "section": "25. CLI / Admin Operations",
        "title": "policies."
    },
    {
        "section": "25. CLI / Admin Operations",
        "title": "learning."
    },
    {
        "section": "25. CLI / Admin Operations",
        "title": "repairs."
    },
    {
        "section": "25. CLI / Admin Operations",
        "title": "rollback."
    },
    {
        "section": "25. CLI / Admin Operations",
        "title": "diagnostics."
    },
    {
        "section": "25. CLI / Admin Operations",
        "title": "همه عملیات مدیریتی مهم هم از UI و هم CLI قابل انجام باشند."
    },
    {
        "section": "26.22 Version-Aware Learning / دانش وابسته به نسخه",
        "title": "ثبت version/release در metadata هر منبع، lesson و knowledge item."
    },
    {
        "section": "26.22 Version-Aware Learning / دانش وابسته به نسخه",
        "title": "ثبت بازه اعتبار زمانی (valid_from / valid_until) برای دانش در صورت امکان."
    },
    {
        "section": "26.22 Version-Aware Learning / دانش وابسته به نسخه",
        "title": "ثبت provider/product/framework و نسخه دقیق مربوط به آموزش."
    },
    {
        "section": "26.22 Version-Aware Learning / دانش وابسته به نسخه",
        "title": "امکان تعیین دستی version و compatibility توسط کاربر."
    },
    {
        "section": "26.22 Version-Aware Learning / دانش وابسته به نسخه",
        "title": "نگهداری چند نسخه از یک موضوع بدون overwrite کردن دانش قبلی."
    },
    {
        "section": "26.22 Version-Aware Learning / دانش وابسته به نسخه",
        "title": "تشخیص deprecated / removed / replaced / improved / unchanged برای هر آموزش یا روش."
    },
    {
        "section": "26.22 Version-Aware Learning / دانش وابسته به نسخه",
        "title": "تشخیص اینکه روش نسخه قدیمی در نسخه جدید همچنان قابل استفاده است یا خیر."
    },
    {
        "section": "26.22 Version-Aware Learning / دانش وابسته به نسخه",
        "title": "جلوگیری از حذف بی‌دلیل دانش قدیمی؛ دانش تاریخی باید حفظ شود ولی وضعیت اعتبار آن مشخص باشد."
    },
    {
        "section": "26.22 Version-Aware Learning / دانش وابسته به نسخه",
        "title": "استفاده از version-aware knowledge در retrieval تا نسخه مناسب task انتخاب شود."
    },
    {
        "section": "26.22 Version-Aware Learning / دانش وابسته به نسخه",
        "title": "تست regression برای جلوگیری از مخلوط‌شدن آموزش نسخه‌های ناسازگار."
    },
    {
        "section": "26.23 Experience + Version Evolution",
        "title": "ثبت نسخه محیط/ابزار/model/framework هنگام ثبت هر experience."
    },
    {
        "section": "26.23 Experience + Version Evolution",
        "title": "ثبت context و شرایط اجرای تجربه."
    },
    {
        "section": "26.23 Experience + Version Evolution",
        "title": "ثبت روش/skill/prompt استفاده‌شده در تجربه."
    },
    {
        "section": "26.23 Experience + Version Evolution",
        "title": "ثبت outcome، failure، recovery و evidence."
    },
    {
        "section": "27. رابط گرافیکی و اجرای بدون دستور / GUI-First Action Layer",
        "title": "GUI Action Registry مرکزی ایجاد شود."
    },
    {
        "section": "27. رابط گرافیکی و اجرای بدون دستور / GUI-First Action Layer",
        "title": "برای هر action قابل‌امنیت، authorization و audit اجباری باشد."
    },
    {
        "section": "27. رابط گرافیکی و اجرای بدون دستور / GUI-First Action Layer",
        "title": "برای عملیات configuration دکمه‌های Save / Reset / Import / Export و نمایش مقدار فعلی و default وجود داشته باشد."
    },
    {
        "section": "27. رابط گرافیکی و اجرای بدون دستور / GUI-First Action Layer",
        "title": "برای provider، model، tool و integration دکمه‌های Add / Edit / Enable / Disable / Delete / Test Connection / Health Check فراهم شود."
    }
]

def roadmap_options() -> list[dict[str, str | bool]]:
    return [{"section": x["section"], "title": x["title"], "completed": True} for x in ROADMAP_OPTIONS]

def roadmap_option_sections() -> list[dict[str, object]]:
    sections: dict[str, list[dict[str, str | bool]]] = {}
    for item in roadmap_options():
        sections.setdefault(str(item["section"]), []).append(item)
    return [{"section": name, "completed": True, "items": values} for name, values in sections.items()]
