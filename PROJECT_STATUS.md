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
- `pytest -q`: **41 passed, 2 warnings**
- `python -m compileall -q my_ai tests`: **موفق**
- CI workflow: **موفق**
- tests workflow: **موفق**

هشدارها مربوط به deprecationهای dependencyهای FastAPI/Starlette و GitHub Actions هستند و شکست تست نیستند.

## 9. وضعیت پیاده‌سازی Roadmap

- اولویت 1: احراز هویت محلی، login/register، first-account-as-admin، session cookie، per-tool allow/deny و audit log پیاده‌سازی شد.
- صفحه ساخت حساب و صفحه ورود اضافه شد. اولین حسابی که در دیتابیس ساخته شود role=admin می‌گیرد و به همه ابزارها دسترسی دارد؛ حساب‌های بعدی user هستند و دسترسی ابزارها به‌صورت جداگانه کنترل می‌شود.
- صفحه مدیریت دانش در `/admin/knowledge` اضافه شد؛ دانش جدید unverified است و admin می‌تواند آن را ویرایش، حذف و verify کند.
- Hybrid retrieval foundation با FTS5 + embedding از Ollama و confidence/provenance اضافه شد؛ مدل embedding پیش‌فرض `bge-m3`.
- Skill Engine foundation با evidence، score، verified و version-aware revalidation اضافه شد.
- streaming chat endpoint، backup/export/import دیتابیس و model health/routing foundation اضافه شد.
- voice adapters برای whisper.cpp و Piper و endpointهای local voice اضافه شد.
- scheduler در بار بالای CPU/RAM pause می‌شود و robots.txt policy برای web fetching در API اضافه شد.
- CI توسعه یافت: `ruff`، `mypy`، `bandit`، `pip-audit`، Docker build و workflow مستقل Ollama E2E.
- dependency source در `pyproject.toml` متمرکز شد و `requirements.txt` به `.[dev]` متصل شد.
- self-update اکنون به‌صورت صریح deny-by-default است و برای activation علاوه بر approval gate به `MYAI_SELF_UPDATE_ENABLED=true` نیاز دارد.
- structured intent router foundation اضافه شد؛ اقدامات پرخطر برای مسیرهای write حساس همچنان باید از policy/permission عبور کنند.

### وضعیت verification

آخرین verification برای commit فعلی موفق است: CI، tests و Ollama E2E همگی سبز هستند. Ruff، mypy، Bandit، pip-audit، pytest و Docker build همگی با موفقیت اجرا شدند.

## 10. کار بعدی

پس از سبز شدن CI، مرحله‌ی بعدی تست محیط واقعی روی سیستم محلی است: ساخت اولین account، بررسی admin access، login/logout، Ollama، hybrid retrieval با `bge-m3` و تست مسیرهای backup/voice. self-update تا زمان policy review و approval صریح فعال نخواهد شد.

## 11. معیار موفقیت یادگیری

`knowledge_coverage`، `concept_score`، `implementation_score`، `debugging_score`، `testing_score`، `real_project_score`، `verified`، `last_verified` و `evidence` باید مستقل نگهداری شوند.

فرمول مفهومی:

`Study → Practice → Execute → Test → Fail → Analyze → Fix → Retest → Verify`

## 12. نکته برای چت‌های آینده

در چت جدید، ابتدا این فایل و سپس وضعیت واقعی `main` بررسی شود و فرض نشود تغییرات چت قبلی هنوز روی branch هستند.

برای موضوع جدید: domain مستقل + curriculum beginner→expert + progress مستقل + weekly review.

برای حافظه: `my_ai/db.py` و `my_ai/memory.py`.

برای پاسخ و مدل: `my_ai/agent.py`، `my_ai/llm.py` و `my_ai/config.py`.

این سند باید بعد از هر update مهم، bug fix، تغییر معماری، تغییر curriculum، تغییر وضعیت تست‌ها یا milestone به‌روزرسانی شود.


### Security hardening verification
- First-account registration is now closed after the first account; administrator user management and per-tool enforcement are present.
- Session cookies are HttpOnly/SameSite and login failure rate limiting is enabled.
- Chat sessions/history are scoped to the authenticated user.
- GitHub writes and security remediation require administrator approval.
- Host-side local DAST execution is blocked; local execution now requires an approved sandbox path. External DAST rejects non-global resolved addresses.
- SQLite enables WAL and foreign-key enforcement; Persian normalization is used for knowledge search/deduplication.
- LLM mode is local-first in auto mode and Ollama context size is configurable with OLLAMA_NUM_CTX.
- Docker image now includes runtime metadata/docs and binds to 0.0.0.0 inside the container.
- Self-update remains deny-by-default and runtime state is ignored by Git.

## Final hardening pass — 2026-09-21

- Enforced exact per-tool permissions for chat/stream, code generation/execution, learning URL, help ask, and other protected routes; no execute-as-wildcard fallback.
- Chat session ownership is checked on read/write paths; legacy unowned sessions are assigned to the first administrator instead of disappearing.
- First-account registration closes immediately after creation; the first-account link is hidden and /register redirects once an account exists.
- Login throttling is bounded and keyed by client plus username; successful authentication clears the failure state. Session cookies use HttpOnly/SameSite and Secure on HTTPS.
- Self-update confirmation phrases are handled consistently and HTTPException is preserved instead of being converted to 502.
- GitHub token mutation requires write permission; Git file paths reject traversal/absolute paths.
- Learning target resolution no longer treats the single-letter c as a substring alias; arbitrary subjects such as learn cooking remain distinct.
- Persian search normalization is applied to indexed/search text, including Arabic/Persian ی/ک and ZWNJ normalization.
- Web robots policy uses bounded HTTP timeouts, validates redirect destinations, and rejects non-global resolved addresses.
- Voice filesystem paths are constrained to data/voice.
- Skill evidence accepts only test/benchmark/official-source evidence with an evidence reference; verification requires multiple evidence kinds.
- Scheduler learning stop no longer disables the weekly review monitor.
- Python execution in Compose is moved behind a dedicated executor service; the main application no longer mounts Docker socket.
- Local DAST remains host-disabled by design and reports sandbox_required rather than claiming a dynamic test ran; external DAST remains explicit-target only.
- Ollama model/context defaults are centralized and aligned with qwen2.5:7b / OLLAMA_NUM_CTX.
- Added regression coverage for registration closure, chat permissions/session isolation, and curly-apostrophe command negation.
- Final verification on the latest commit: tests workflow successful, CI successful, Ollama E2E successful; CI included compileall, Ruff, mypy, Bandit, pip-audit, pytest, Docker build, and Docker Compose configuration validation.