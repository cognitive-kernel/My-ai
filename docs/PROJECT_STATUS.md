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

- حذف وابستگی اصلی به keywordهای شکننده.
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
- اجرای compile/test قبل از activate.
- health check پس از activate.
- rollback خودکار در صورت failure.
- ثبت failure lesson بدون فعال‌سازی خودکار آن.

### زیرساخت Configuration و Provider

- Configuration Registry اکنون schema version دارد و migration registry جداگانه برای تکامل schema ایجاد شده است.
- هر setting ثبت‌شده نسخه‌ی metadata دارد و مقدار ذخیره‌شده نیز schema version خود را نگه می‌دارد.
- APIهای Registry نسخه‌ی schema را در پاسخ export/import/registry اعلام می‌کنند.
- قرارداد عمومی `LLMProviderAdapter`، capability/health/token-usage metadata و `ProviderRegistry` اضافه شده است؛ انتخاب runtime در `create_llm` از این registry عبور می‌کند.
- `ModelManager` برای custom OpenAI-compatible provider inventory و health-check دارد، بدون اینکه Agent به API provider وابسته شود.

### LLM سفارشی

- Provider فعال اکنون از Configuration Registry قابل انتخاب است.
- مسیر custom-openai-compatible برای اتصال LLM اختصاصی دارای endpoint، model ID و API key است.
- API key به‌صورت secret در settings ذخیره می‌شود و در export عادی تنظیمات قرار نمی‌گیرد.
- Semantic Router نیز از همین Provider سفارشی استفاده می‌کند.
- برای APIهای کاملاً اختصاصی و غیر OpenAI-compatible هنوز Adapter عمومی لازم است.

## 5. زیرساخت‌های جدید در ادامه نقشه جامع

- Provider Adapter و Provider Registry برای جدا کردن Agent/runtime از protocolهای LLM ایجاد شده‌اند.
- Provider/Model Catalog پایدار با metadata، capability، version، priority و enabled state اضافه شده است.
- API مدیریت provider/model و export catalog در Settings ایجاد شده است.
- Model Manager اکنون catalog پایدار را نیز در inventory و fallback chain لحاظ می‌کند.
- Event Bus، Execution Budget، Versioned Cache و Parallel Execution به‌عنوان primitives لایه Agent پیشرفته اضافه شده‌اند.
- Configuration Registry اکنون import/export را از UI نیز در اختیار دارد.
- این قابلیت‌ها تا اجرای تست‌های واقعی و regression verification، در roadmap به‌عنوان تکمیل‌شده علامت نخورده‌اند.
- Context assembly با priority/budget و verification با evidence/confidence نیز به‌صورت primitive مستقل اضافه شده‌اند.
## GUI-First Action Layer

- `my_ai/ui_actions.py` provides a central registry for graphical quick actions with module, permission, endpoint and confirmation metadata.
- Settings exposes `/settings/ui-actions` and a graphical Action Center.
- Learning course cards now expose Start/Resume and Pause controls instead of requiring a command/API call.
- The roadmap now requires graphical equivalents for actionable modules wherever technically and securely possible.
- Provider/Model Catalog now has graphical add/list/delete controls in Settings; model registration is also available without editing configuration files.
- Learning now exposes Start/Resume and Pause controls in the Settings course cards.


### GUI/CLI parity — provider/model catalog
- Provider catalog now supports graphical enable/disable, deletion, connection health checks, and version/capability metadata.
- Model catalog now supports graphical enable/disable, deletion, health checks, and version/capability metadata.
- The same provider/model lifecycle is available from `scripts/myai_catalog.py` for command-line operation.
- GUI lifecycle routes are covered by `tests/test_provider_model_gui.py`.


### No-code control-plane implementation pass
- Added unified persistent control plane for agent behavior, workflows, tools, memory, research, security, self-update/repair, scheduler, execution, integrations, observability, backup, prompts/policies, evaluation and experience evolution.
- Added schema-driven Settings access to control-plane records and action lifecycle.
- Added CLI parity through `scripts/myai_control.py` and `scripts/myai_admin.py`.
- Added advanced orchestration primitives: dynamic skills, knowledge graph, hybrid retrieval, context planning, confidence, evaluation lab, research pipeline, secure environment, task graph, smart cache, execution budgets, event workflows, meta-agent and Agent OS.
- Added version-aware knowledge/experience evolution and learning source catalog with approval/provenance.
- Added provider/model routing selection and capability-aware fallback infrastructure.
- This implementation pass is intentionally not marked test-complete yet; verification/regression is deferred to the requested next phase.


### آخرین pass پیاده‌سازی بدون تست
- ویرایش Provider از GUI/CLI، مدیریت چند کلید و rotation در مسیر مشترک Catalog اضافه شد.
- عملیات Configuration Registry در CLI با GUI هم‌تراز شد: set/reset/import/export/history.
- تاریخچه تغییرات تنظیمات در DB ثبت و از Settings قابل مشاهده API شد.
- طبق دستور پروژه، در این pass هیچ test/CI/regression اجرا نشده است.

### Latest implementation pass — 2026-10-02
- Unified admin CLI now covers configuration profiles, backup/restore, learning-source catalog operations and capability inventory in addition to control-plane CRUD/action lifecycle and provider/model administration.
- Settings exposes configuration-profile management through the same persistent control plane.
- GUI Action Registry exposes profile and capability discovery.
- No-code runtime adapters now expose learning, security, scheduler, integration, evaluation, regression, budget, cache, skills and knowledge-graph namespaces directly to runtime consumers.
- Verification remains intentionally deferred; no tests or CI were executed.


### Final coding pass before verification — 2026-10-02
- Completed the generic Settings Control Plane GUI lifecycle for record create/edit/enable/disable/delete and operation start/status/update, including progress, result and error state.
- Expanded the central GUI Action Registry for configuration history, provider/model catalog, learning catalog, database policy, security roles and evaluation/regression.
- GUI and CLI continue to share the persistent Control Plane rather than maintaining separate state stores.
- This marks the end of the requested implementation-first pass; test, regression, integration and runtime verification remain intentionally unstarted.
