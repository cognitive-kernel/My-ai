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

- embedding محلی با Ollama؛ مدل پیش‌فرض پروژه `nomic-embed-text` است تا با تنظیمات runtime هم‌راستا باشد.
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

### 2026-09-26 — Learning stability, scheduler diagnostics and router hardening

- 33d42724 — resilience no longer overwrites LearningEngine._retry_with_limit; bounded retry policy remains authoritative.
- 6ab19d30 — lesson and assessment stages now use bounded retries; web-source failures can fall back to previously stored local knowledge instead of making the learning pipeline dependent on successful web retrieval.
- 0db458b3 — scheduler logs full worker exceptions with language, stage and consecutive-error count using logger.exception, while preserving the DB status/error snapshot.
- c87018b2 — router adds explicit security_scan, help and file_analysis intents and retains deterministic high-risk routing.
- 572f9b6e, d6ce8a3a, 26b702e3 — regression coverage for retry-policy integrity, new router intents/execution ambiguity and scheduler exception logging.
- Structured router arguments remain available for language, topic, goal, project path and URLs; session context is passed from chat and streaming paths.
- Self-update remains deny-by-default; health checks are restricted to loopback and arbitrary restart command overrides are not accepted.

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
- Hybrid retrieval کامل با FTS5 + `nomic-embed-text`، content-hash embedding cache، provenance/citation اجباری و confidence calibration مبتنی بر retrieval judgments پیاده‌سازی شد.
- Skill Engine کامل‌تر شد: knowledge coverage و verified skill score مستقل، evidence immutable و قابل مشاهده، sandbox benchmark و version-aware revalidation.
- streaming chat endpoint، backup/export/import دیتابیس و model health/routing foundation اضافه شد.
- voice adapters برای whisper.cpp و Piper و endpointهای local voice اضافه شد.
- scheduler در بار بالای CPU/RAM pause می‌شود و robots.txt policy برای web fetching در API اضافه شد.
- CI توسعه یافت: `ruff`، `mypy`، `bandit`، `pip-audit`، Docker build و workflow مستقل Ollama E2E.
- dependency source در `pyproject.toml` متمرکز شد و `requirements.txt` به `.[dev]` متصل شد.
- self-update اکنون به‌صورت صریح deny-by-default است و برای activation علاوه بر approval gate به `MYAI_SELF_UPDATE_ENABLED=true` نیاز دارد.
- structured intent router foundation اضافه شد؛ اقدامات پرخطر برای مسیرهای write حساس همچنان باید از policy/permission عبور کنند.

### وضعیت verification

آخرین verification برای commit فعلی موفق است: CI، tests و Ollama E2E همگی سبز هستند. Ruff، mypy، Bandit، pip-audit، pytest و Docker build همگی با موفقیت اجرا شدند.

## 10. وضعیت نهایی hardening

### Completed repository-level backlog

- معماری: core/domain packages اضافه شدند؛ router به domain/router منتقل و my_ai/router.py به compatibility facade تبدیل شد و protocolهای core ثبت شدند.
- Router: structured/schema-first routing و regression برای intentهای مبهم فعال است؛ fallback deterministic فقط مسیر resilience است.
- Retrieval: FTS5 + Ollama embeddings + hybrid scoring + provenance + verified filtering + empirical confidence calibration فعال است.
- Knowledge: UI مدیریت دانش، verification و audit trail فعال است؛ delete به soft-delete تبدیل شده تا تاریخچه حفظ شود.
- Skill Engine: evidence، sandbox benchmark، score مستقل و version-aware revalidation فعال است.
- Policy: deny-by-default API policy، correlation ID و read-only enforcement در route و database mutation boundary فعال است.
- Self-update: approval gate، enable flag، clean-tree check، isolated worktree، pre-update tag snapshot، test gate، watchdog/health و rollback path فعال است و همچنان deny-by-default می‌ماند.
- Scope: architecture/protocol boundaries و feature-creep guardrails مستند و enforced-by-test شده‌اند؛ curriculumهای جانبی optional باقی می‌مانند و core dependency ندارند.
- Eval: retrieval baseline، calibration data و regression tests در CI قرار دارند.
- E2E: browser smoke/file workflow و surface checks برای learning/voice/GitHub/self-update/knowledge/skills فعال است.
- Voice: whisper.cpp/Piper discovery + health probes + offline readiness و semantic media analysis فعال است.
- Dependencies: pyproject.toml تنها source of truth است؛ requirements.txt خالی و compatibility-only است؛ requirements.lock snapshot موجود است.
- Scheduler/Web: resource guard، robots policy، public-address validation و timeout/backoff موجود است.
- Streaming/multi-session/backup: streaming، session isolation و backup/export/import با format version + SHA-256 integrity فعال است.
- Models: per-role availability و fallback readiness در health endpoint ثبت می‌شود.
- Observability: structured JSON logging، request correlation ID و HTTP metrics فعال است.
- Startup: python -m my_ai و uvicorn my_ai.api:app از startup prerequisite gate یکسان استفاده می‌کنند.
- README: gapهای کدنویسی قبلی با implementation واقعی همگام شدند؛ فقط محدودیت‌های ذاتی host-level و نبود uv.lock در محیط offline صریح باقی مانده‌اند.
- Issues: #52، #33 و #24 با وضعیت implementation فعلی آماده بسته‌شدن هستند و پس از verification نهایی باید بسته شوند.

### Verification gate

Verification نهایی repository-level برای commit d83cff4d5d4ae579eb596d4bf41e53f8a38200e3 سبز است: CI run 36298379858، browser E2E run 36298379845 و Ollama E2E run 36298379864 همگی success شدند؛ CI شامل compileall، ruff، mypy، bandit، pip-audit، pytest (200 passed)، Docker build و docker compose config است. این به معنی 100% verification عملیاتی روی هر ماشین نیست: کنترل write فرآیندهای خارجی OS خارج از اختیار برنامه است، اجرای واقعی whisper.cpp/Piper به engine/model محلی نیاز دارد و uv.lock در محیط توسعه بدون شبکه تولید نشده است.

## 10. کار بعدی

کار بعدی فقط verification عملیاتی روی ماشین مقصد است: اجرای pytest/compile/lint/security audit، browser E2E، Ollama E2E، بررسی health مدل‌ها، voice engines و backup integrity. self-update عمداً تا زمان approval صریح فعال نمی‌شود.

git pull

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
- LLM mode is local-first in auto mode and Ollama context size is configurable with OLLAMA_NUM_CTX; the CPU profile defaults to 2048.
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

## 13. 2026-09-26 — Completion hardening pass

- 42f5c600 — /learning/status no longer loads or returns the large learning_sessions.notes field; session payloads are explicitly sanitized. This prevents the observed FastAPI/JSON serialization MemoryError.
- cb3e0c95, 20379360 — router now has an LLM-assisted classification path for ambiguous requests, with deterministic fallback and deterministic authority retained for high-risk intents. ROUTER_MODEL and ROUTER_LLM_ENABLED control the routing model/path.
- 1a55dcc0 — Skill Engine evidence is version-tagged and revalidate() now rechecks evidence freshness, recalculates verification, and invalidates stale evidence.
- 1356a11d — voice module now reports binary/model readiness and exposes a complete local STT-to-text-to-TTS roundtrip helper. Offline readiness is only true when both engines and both models are present.
- 75c13444 — batch Ollama embeddings now use the same endpoint validation as single embeddings, including offline-strict loopback enforcement.
- d0f7d521, 60fc0709 — regression coverage added for LLM-assisted routing.
- ed6d4b56 — regression coverage added for skill evidence revalidation.
- b0b4c59b — regression coverage added for the offline voice roundtrip.
- 7ab7b643, 680b2cd4 — regression coverage added to ensure learning status never exposes lesson notes.
- f3b4ec8f — CI now cancels stale runs for the same ref instead of accumulating unnecessary queued runs.
- efcb75c0 — duplicate tests.yml workflow removed; CI checks are centralized in ci.yml.
- 225bd321 — Ollama E2E now includes an authenticated /learning/status smoke test.
- 06fdcaf3 — ROUTER_LLM_ENABLED is documented in .env.example.

### Current verification boundary

The repository changes above are implemented and covered by regression tests, but they do not prove every local runtime dependency is installed on the user's machine. Full production claims still require the local Ollama/Whisper/Piper binaries and models to be exercised. GitHub Actions can verify the configured CI environment; it cannot certify the user's Windows runtime.

### Remaining verification boundary

- Semantic retrieval uses FTS5 + Ollama embeddings + cosine similarity; confidence is calibrated with persisted retrieval judgments using monotonic isotonic empirical calibration and remains explicitly uncalibrated until sufficient judgments exist.
- Voice is local/offline in the application path: MediaRecorder → local upload → whisper.cpp → chat → Piper. Actual Whisper/Piper binaries and models still require verification on the target machine.
- Browser UI E2E now runs on pull requests and covers authenticated dashboard/API surfaces; final target-machine UI verification remains required.
- Self-update remains deny-by-default and requires explicit approval plus the runtime enable flag.
- Final repository-wide pytest/compile/security verification must be run after the current hardening commits settle in CI; the target Windows runtime still needs the final local verification.


## 14. 2026-09-26 — Learning runtime hardening follow-up

Implemented in the current main branch:
- learning prerequisite discovery no longer consumes a second LLM call; prerequisites are derived from curriculum order;
- per-source web extraction no longer invokes an LLM for every URL; fetched source text is stored as evidence for the single lesson synthesis call;
- lesson assessment is deterministic/local and therefore cannot fail because of a second model call;
- web-source fetches have bounded timeouts, bounded payload size, per-host rate limiting, and cancellation propagation;
- model/resource waits are bounded instead of potentially waiting forever;
- scheduler learning concurrency is capped by LEARNING_MAX_CONCURRENT_WORKERS;
- skill evidence now tracks independent concept/implementation/source/reliability metrics;
- Ollama CI startup/model-pull diagnostics and retries were hardened;
- authenticated browser smoke coverage was added for learning, scheduler, voice, knowledge, skills, self-update and self-repair surfaces.

Verification boundary: GitHub-side code and test changes are committed, but a claim of 100% runtime closure still requires the target machine's local test suite and actual Whisper/Piper/Ollama installations to execute successfully.
- retrieval confidence now has an empirical calibration path: admin judgments are persisted and confidence is only emitted as calibrated after sufficient same-score-bucket judgments; otherwise it is explicitly marked uncalibrated;
- application read-only mode now blocks key project, voice-output, and self-update writes and avoids import-time directory creation in read-only mode.
- Unified permission policy و process-wide OS/database read-only enforcement روی writerهای اصلی و مسیرهای API اعمال شد.
- Knowledge management UI در `/admin/knowledge` و Skill Engine UI در `/admin/skills` با verification/evidence workflow فعال شد.


## Current hardening follow-up — 2026-09-27

- Unified policy coverage now has a regression check for every non-public API route.
- Direct SQLite knowledge writers honor `MYAI_READ_ONLY=true`, and embedding-cache writes honor the same dynamic read-only flag.
- Encrypted backup creation was made type-safe and has explicit verification coverage.
- Browser voice no longer uses `SpeechRecognition` or `speechSynthesis`; it uses local MediaRecorder plus the local Whisper/Piper endpoints.
- Browser voice recordings are normalized with FFmpeg when Whisper cannot consume the browser container directly.
- Chat-to-document conversion preserves headings, paragraphs and lists for DOCX/XLSX/PDF/PPTX.
- Retrieval confidence calibration uses isotonic empirical calibration rather than per-bucket Laplace smoothing.
- Dependency tests now require every runtime dependency declared in `pyproject.toml` to be pinned in `requirements.lock`.


## 15. 2026-09-27 — Hardening completion pass in progress

Repository-level fixes added on the layered branch:
- policy actions are now method-specific, parameterized routes are matched centrally, and unmapped routes are denied for administrators as well as regular users;
- central HTTP audit records actor identity, request correlation, input/output hashes and sizes, status, content type and streaming metadata without storing raw request secrets;
- chat intent routing no longer uses keyword tables for learning/coding/help/image intent selection; structured router arguments provide the requested language;
- backup format v4 exports the complete application state; sensitive identity/permission/audit tables are included only in encrypted exports and import rejects plaintext sensitive payloads;
- scheduler workers use a persisted cross-process lease with renewal/release so multiple application processes cannot independently run the same language worker;
- skill evidence expires after 30 days and version changes invalidate verification;
- voice health now includes FFmpeg readiness because browser recordings may require local container normalization;
- the eval harness now contains a fixed Persian response baseline and the Ollama E2E workflow executes a live semantic-router/response-quality baseline on pull requests;
- browser smoke coverage includes the knowledge-management and Skill Engine UI pages;
- self-update creates a SQLite database snapshot before activation and the watchdog restores that snapshot together with the tagged source revision on failed health activation.

These changes are not considered final until CI, browser E2E, Ollama E2E and the target Windows test suite are green after this pass.


## 16. 2026-09-27 — Repository hardening verification complete

Final branch head: 6e480c2d18464a335bd00a7efd9f292112a024db.

Verified in GitHub Actions for this head:
- CI: success — compileall, Ruff, mypy, Bandit, pip-audit, full pytest, Docker build and Compose validation.
- Browser E2E: success.
- Ollama E2E: success — Ollama startup/model smoke, automated Persian response baseline, authenticated API/UI smoke, and Docker Compose E2E.

Additional completion items in this pass:
- method-specific central permission actions and deny-by-default for unmapped routes including administrators;
- structured audit event metadata with actor/request ID/input-output hashes;
- no keyword intent tables in the main chat intent selection;
- complete versioned backup export/import with encrypted sensitive-state handling;
- persisted scheduler worker leases;
- evidence age/version revalidation for skills;
- offline voice readiness plus media-container readiness;
- dependency lock is installed by CI rather than only checked;
- allowlisted cross-platform system prerequisite catalog for Git, FFmpeg and Nmap;
- self-update database snapshot and rollback support.

Operational boundary: application-level read-only cannot revoke write privileges from arbitrary unrelated processes running outside My-AI, and actual Whisper/Piper model/binary availability remains a property of the target machine. These are host/runtime prerequisites, not unimplemented repository routes.


## 2026-09-27 — Post-merge verification

PR #57 is merged into `main`. PR #56 is closed because its implementation was carried into the current-main hardening branch. Generic confirmed OS package installation is exposed through the admin-only system prerequisite endpoint and uses native package managers without shell execution. Target-machine acceptance diagnostics are available at `scripts/target_acceptance.py`. GitHub Actions CI/E2E verification for the hardening branch passed before merge; target-machine Whisper/Piper availability remains environment-dependent.
