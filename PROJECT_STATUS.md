# My-AI — Project Status & Handoff

> این فایل مرجع دائمی وضعیت پروژه است. بعد از هر تغییر مهم باید به‌روزرسانی شود تا در چت جدید یا بعد از پاک‌شدن تاریخچه، وضعیت پروژه قابل بازیابی باشد.

## 1. هدف پروژه

My-AI یک دستیار هوش مصنوعی محلی است که هدف آن داشتن حافظه، دانش قابل توسعه، توانایی یادگیری، کار با کد و دیتابیس، تشخیص و رفع خطا، و در آینده به‌روزرسانی امن خودش با تأیید کاربر است.

اصول کلیدی: یادگیری با مطالعه، تمرین، اجرا، تست و evidence؛ جداسازی knowledge coverage از verified skill؛ self-update با snapshot/test/health-check/rollback؛ استقلال progress هر domain؛ progress از 0 تا 100 با گام دقیق 0.5%.

## 2. مخزن

- Repository: `cognitive-kernel/My-ai`
- Branch: `main`
- Local clone: `D:\Projects\MY-AI`

## 3. وضعیت فعلی

### Learning / Knowledge

Python و SQL Server curriculumهای جداگانه از مبانی تا مباحث پیشرفته دارند. Python حوزه‌هایی مثل syntax، OOP، data model، decorators/descriptors/metaclasses، generators، typing، async/concurrency، networking، testing/debugging/profiling، packaging، performance، CPython internals و security را پوشش می‌دهد. SQL Server حوزه‌هایی مثل T-SQL، طراحی دیتابیس، joins/CTE/window functions، procedures/functions/triggers، transactions/locking/deadlocks، indexes/statistics، execution plans، optimization، security، backup/restore، HA/DR، monitoring و internals را پوشش می‌دهد.

### Dynamic learning domains

موضوع یا زبان جدید از درخواست کاربر استخراج می‌شود؛ اگر موجود باشد همان domain ادامه پیدا می‌کند و اگر جدید باشد domain مستقل در `learning_domains` ساخته می‌شود. curriculum جدید از beginner تا expert با prerequisites، fundamentals، advanced، internals، security، testing، debugging، performance، architecture، production و capstone ساخته می‌شود و در progress مستقل نمایش داده می‌شود. داده‌های قبلی reset نمی‌شوند.

فایل‌ها: `my_ai/dynamic_learning.py`، `my_ai/domain_registry.py`، `my_ai/scheduler.py`.

### Weekly knowledge maintenance

پس از تکمیل domain، review هفتگی ثبت می‌شود. هر 7 روز منابع رسمی و در صورت نیاز وب بررسی می‌شوند؛ فقط تغییرات واقعی و جدید به curriculum اضافه می‌شوند و دوباره وارد learning/verification می‌شوند. نبود تغییر نیز ثبت می‌شود و review بعدی 7 روز بعد است.

### Memory deduplication

حافظه‌ی دانشی content-addressed است. محتوای normalize‌شده با SHA-256 شناسه‌گذاری می‌شود؛ یک محتوای یکسان فقط یک بار ذخیره می‌شود. duplicateهای قدیمی هنگام startup حذف می‌شوند، source بهتر روی رکورد موجود حفظ می‌شود، unique index روی `content_hash` از duplicate جدید جلوگیری می‌کند و FTS5 پس از migration rebuild می‌شود.

فایل‌ها: `my_ai/db.py`، `my_ai/memory.py`.

مرحله بعدی: semantic similarity برای تشخیص مطالب مشابه ولی غیر یکسان.

### Database learning

SQLite دیتابیس فعلی خود My-AI است و curriculum مستقل دارد. SQL Server و MySQL نیز curriculum مستقل دارند. هدف این است که دیتابیس‌های مورد استفاده‌ی واقعی پروژه از نظر طراحی، query، indexing، transactions، reliability و performance نیز یاد گرفته شوند.

### Response quality / LLM backend

قواعد پاسخ‌گویی برای زبان کاربر و به‌خصوص فارسی تقویت شده‌اند: grammar، spelling، punctuation، نیم‌فاصله و ساختار طبیعی؛ همچنین مدل باید consistency را قبل از پاسخ مرور کند و ادعای بدون evidence نداشته باشد.

Backendها:

- پیش‌فرض: Ollama محلی.
- اختیاری: OpenAI-compatible Responses API.
- فعال‌سازی: `LLM_PROVIDER=openai`.
- کلید فقط از `OPENAI_API_KEY` خوانده می‌شود و نباید در Git ذخیره شود.
- مدل پیش‌فرض: `gpt-5.6-luna` و قابل تنظیم با `OPENAI_MODEL`.
- اتصال مستقیم به runtime همین گفت‌وگو وجود ندارد؛ اتصال از طریق API انجام می‌شود.

### Progress

Progress بر اساس topicهای یکتا و متعلق به همان curriculum محاسبه می‌شود، از 100% عبور نمی‌کند و فقط روی grid نیم‌درصدی قرار می‌گیرد. تغییر domain، worker قبلی را متوقف می‌کند و progressها مستقل هستند. مطالب جدید weekly review نیز پس از verification به progress همان domain اضافه می‌شوند.

### Self-update / self-repair

هدف معماری: inspect → diagnose → proposal → user approval → snapshot → isolated worktree → compile/test → activate → health check/watchdog → rollback → failure lesson.

## 4. نقشه راه اولویت‌بندی‌شده جدید

این موارد به‌عنوان backlog رسمی پروژه ثبت شده‌اند و ترتیب آن‌ها عمداً از امنیت و کنترل شروع می‌شود و self-update در آخر قرار دارد.

### اولویت 1 — احراز هویت و سیستم دسترسی ابزارها

- احراز هویت مناسب برای عملیات حساس.
- مجوز مستقل `allow/deny` برای هر ابزار.
- audit log کامل از اجرای ابزارها و تمام عملیات write.
- اصل deny-by-default برای ابزارها و عملیات پرخطر.
- ثبت actor، ابزار، زمان، ورودی/خروجی قابل ثبت، نتیجه و خطا در audit trail.
- تفکیک دسترسی خواندن، نوشتن، اجرا و عملیات سیستمی.

### اولویت 2 — بازیابی معنایی و Hybrid Search

- embedding محلی با Ollama؛ گزینه‌ی اولیه برای بررسی: `bge-m3` با توجه به پشتیبانی چندزبانه و فارسی.
- ترکیب semantic similarity با FTS5 در یک hybrid retrieval pipeline.
- نگهداری provenance و منبع برای نتایج بازیابی.
- نمایش ارجاع به منبع در پاسخ‌ها.
- محاسبه و نمایش confidence با تعریف و calibration مشخص، نه یک عدد حدسی.
- semantic similarity برای مطالب مشابه ولی غیر یکسان.

### اولویت 3 — صفحه مدیریت دانش

- مشاهده، ویرایش، حذف و تأیید یادداشت‌ها/knowledge items.
- وضعیت پیش‌فرض «تأییدنشده» برای دانش جدید.
- انتقال به verified فقط پس از test موفق یا تأیید منبع رسمی.
- نمایش source/provenance، وضعیت verification و تاریخ آخرین تأیید.
- امکان audit تغییرات دانش.

### اولویت 4 — Skill Engine واقعی

- اجرای همان Universal Learning & Skill Engine موجود در نقشه راه.
- آزمون نظری و taskهای coding/debugging.
- اجرای sandboxed و regression testing.
- evidence قابل مشاهده برای هر skill.
- امتیاز skill مستقل از knowledge coverage.
- version-aware revalidation پس از تغییر نسخه‌ی dependency، runtime یا منبع دانش.
- یادگیری مجدد مباحث ضعیف بر اساس نتیجه‌ی آزمون و evidence.

### اولویت 5 — Streaming، چندسشن و Backup

- streaming پاسخ‌ها.
- پشتیبانی از چند session مستقل گفتگو.
- export/import داده‌ها.
- backup و restore دیتابیس با مسیر امن و قابل اعتبارسنجی.
- مدیریت lifecycle و سازگاری نسخه‌ی export/import.

### اولویت 6 — مدیریت مدل

- مدل کوچک‌تر برای routing/classification.
- مدل قوی‌تر برای coding و وظایف پیچیده.
- fallback بین مدل‌ها.
- health check برای مدل و backend.
- ثبت وضعیت availability و خطاهای model routing.

### اولویت 7 — Router قابل اعتماد

- حذف وابستگی اصلی به keywordهای شکننده مانند «یاد بگیر» یا «پن‌تست».
- استفاده از function calling یا classifier ساده و قابل تست.
- schema مشخص برای intent و tool arguments.
- تأیید صریح کاربر برای اقدام‌های پرخطر.
- تست regression برای intent routing و مرزهای مبهم.

### اولویت 8 — صدای کاملاً آفلاین

- speech-to-text محلی با `whisper.cpp`.
- text-to-speech محلی با Piper.
- عدم وابستگی voice pipeline به سرویس ابری.
- health check و fallback مناسب برای نبودن مدل/engine صوتی.

### اولویت 9 — Eval Harness

- مجموعه تست ثابت برای کیفیت retrieval.
- مجموعه تست ثابت برای کیفیت پاسخ فارسی.
- اجرای خودکار پس از تغییرات مرتبط.
- ثبت baseline و مقایسه‌ی نتایج قبل/بعد.
- جلوگیری از regression در retrieval، citation، confidence و پاسخ فارسی.

### اولویت 10 — مدیریت منابع Scheduler و Web Fetching

- سقف مصرف CPU و RAM برای workerها.
- توقف یا کاهش فعالیت هنگام بار غیرعادی سیستم.
- کنترل concurrency.
- رعایت `robots.txt` در دریافت وب، در حدی که برای crawler/fetcher پروژه قابل اعمال باشد.
- رعایت rate limit و backoff.
- ثبت fetch failures و rate-limit events.

### اولویت 11 — CI قوی‌تر و یک منبع dependency

- افزودن `ruff`.
- افزودن `mypy`.
- افزودن `bandit`.
- افزودن `pip-audit`.
- build آزمایشی Docker در CI.
- تست e2e با Ollama.
- ایجاد single source of truth برای dependencyها و جلوگیری از drift بین `requirements.txt` و `pyproject.toml`.
- حفظ تست‌های موجود و اضافه کردن verificationهای جدید بدون حذف regression coverage.

### اولویت 12 — Self-update با Snapshot و Rollback

این مورد عمداً آخرین اولویت است و باید **deny-by-default** باشد.

معماری هدف:

inspect → diagnose → proposal → explicit user approval → snapshot → isolated worktree → compile/test → activate → health check/watchdog → rollback → failure lesson

الزامات امنیتی:

- هیچ self-update یا write خطرناک بدون مجوز صریح اجرا نشود.
- snapshot قبل از تغییر.
- اجرای تغییر در محیط ایزوله.
- تست و health check اجباری قبل از activation.
- rollback قابل اعتماد در صورت failure.
- ثبت کامل عملیات در audit log.
- محدودیت مسیرها، ابزارها و دسترسی‌های قابل استفاده توسط updater.
- جلوگیری از اجرای arbitrary code خارج از policy مجاز.

## 5. GitHub authentication

مسیرهای OAuth/CLI و token موجود هستند. credential واقعی نباید داخل repository ذخیره شود.

## 6. مستندات کمک

`docs/help/` شامل راهنماهای chat، learning، coding، security، github، memory، scheduler، voice، api و docker است.

## 7. تغییرات این مرحله

- `4719215` — Fix scheduler status API endpoint and add scheduler status regression coverage
- Root cause: `my_ai/api.py` called `scheduler.status()`, while the refactored `StudyScheduler` no longer exposed that method.
- Fix: restored a JSON-safe `StudyScheduler.status()` snapshot including `running`, `language`, `stage`, `current_topic`, `last_result`, `error` and `interval_seconds`.
- Regression test: `tests/test_learning_progress.py` verifies scheduler status behavior.

- `6fcf5fd5238e7a52f6dd1a772e1ad08356610be4` — Deduplicate knowledge storage and prepare database learning metadata
- `2d6d5ffb301697f7dcc33e722cf8fa3e25a58313` — Use content-addressed memory to prevent duplicate knowledge
- `f3b79a4d620b5891643099ea766952a1f271414e` — Add optional OpenAI-compatible model configuration
- `6dbd3122244b188b7cb286d9ff20fe83bc3a0da7` — Add optional OpenAI Responses API backend
- `c4d34f831369a165c6494a8afc488f5b1a1bd605` — Improve response quality and use configured LLM backend
- `908f6d03fb6540a383d73a15fa24bc794250c67f` — Use configured LLM backend for autonomous learning
- `725d51627e91ee23105588acec533d593256846f` — Add regression tests for memory deduplication
- `1fc7f688ac8b3c8dda4224e5f9c42751fdc96446` — Finalize project status after successful deduplication and LLM tests

- Local runtime configuration verified: `.env` was created from `.env.example` and `OLLAMA_MODEL` was aligned to the installed Ollama model `qwen2.5:7b`. This is a local environment change and is not committed as project code.

## 8. تست و CI

آخرین verification برای این مرحله موفق است:

- `python -m pytest tests/test_learning_progress.py -q`: **6 passed in 0.13s**
- `pytest -q`: **31 passed, 2 warnings**
- `python -m compileall -q my_ai tests`: **موفق**
- CI workflow: **موفق**
- tests workflow: **موفق**

هشدارها مربوط به deprecationهای dependencyهای FastAPI/Starlette و GitHub Actions هستند و شکست تست نیستند.

## 9. کار بعدی

بر اساس اولویت جدید، شروع implementation باید از **اولویت 1: احراز هویت و سیستم دسترسی ابزارها** باشد؛ سپس مراحل 2 تا 12 به‌ترتیب اجرا شوند.

## 10. معیار موفقیت یادگیری

`knowledge_coverage`، `concept_score`، `implementation_score`، `debugging_score`، `testing_score`، `real_project_score`، `verified`، `last_verified` و `evidence` باید مستقل نگهداری شوند.

فرمول مفهومی:

`Study → Practice → Execute → Test → Fail → Analyze → Fix → Retest → Verify`

## 11. نکته برای چت‌های آینده

در چت جدید، ابتدا این فایل و سپس وضعیت واقعی `main` بررسی شود و فرض نشود تغییرات چت قبلی هنوز روی branch هستند.

برای موضوع جدید: domain مستقل + curriculum beginner→expert + progress مستقل + weekly review.

برای حافظه: `my_ai/db.py` و `my_ai/memory.py`.

برای پاسخ و مدل: `my_ai/agent.py`، `my_ai/llm.py` و `my_ai/config.py`.

این سند باید بعد از هر update مهم، bug fix، تغییر معماری، تغییر curriculum، تغییر وضعیت تست‌ها یا milestone به‌روزرسانی شود.
