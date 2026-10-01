# My-AI — Consolidated Project Documentation

> Consolidated from all Markdown documentation except `README.md`. Source paths are retained as section labels.


---

# Source: `ARCHITECTURE.md`

# My-AI Architecture Boundaries

## Runtime layers

1. API/UI — my_ai/api.py and my_ai/static/; HTTP/authentication/transport only.
2. Application — my_ai/application/; dependency injection and use-case composition.
3. Domain — my_ai/domain/; pure business decisions and schemas. Domain code depends only on my_ai/core and standard-library code.
4. Core — my_ai/core/; stable protocols and shared contracts with no infrastructure/application imports.
5. Infrastructure — my_ai/infra/; LLM, persistence, network and host adapters.

Legacy top-level modules such as my_ai/router.py, my_ai/llm.py and my_ai/db.py are compatibility facades only. New code must import the layered implementation directly.

## Dependency enforcement

The dependency graph is enforced by tests/test_architecture_boundaries.py using AST import inspection:

- Domain cannot import API/UI, application, infrastructure, database, LLM or configuration adapters.
- Core cannot import application/domain/infrastructure/API packages.
- Application cannot import API/UI; external adapters are injected through core protocols.
- Infrastructure cannot import application or API layers.
- Critical flat modules are verified to contain no implementation of routing, LLM or persistence.

## Router boundary

The router is a domain service with the StructuredRouter protocol injected by the application layer. Provider adapters live in my_ai/infra/router_llm.py.

Routing uses strict schema-constrained structured output; there is no keyword/regex intent table or free-form JSON fallback. The router only returns intent data. Authorization, confirmation and execution remain separate policy concerns.

## Persistence boundary

SQLite implementation lives in my_ai/infra/persistence.py. my_ai/db.py remains a compatibility facade for existing integrations.

## Acceptance surfaces

/admin/readiness, /eval/retrieval, /skills/reviews, /self-update/status, and the browser E2E suite expose operational acceptance state.

Self-update remains disabled by default; enabling it requires the explicit runtime enable flag and explicit approval.

---

# Source: `CONTRIBUTING.md`

# Contributing

## Development

- Python 3.11+.
- Install development dependencies with `pip install -e '.[dev]'`.
- Run `python -m compileall -q my_ai tests`.
- Run `pytest -q`.
- Run `ruff check my_ai --select F`.
- Run `mypy my_ai --ignore-missing-imports`.
- Run `bandit -r my_ai -q -lll`.
- Run `pip-audit`.

## Changes

Keep changes focused. New write/execute API routes must be registered in `my_ai/access_policy.py` and tested.
Do not commit credentials, tokens, database files, generated artifacts, or local settings keys.

## Security-sensitive changes

Changes to authentication, permissions, sandboxing, self-update, self-repair, GitHub access, or external security tooling require regression tests and a clear audit trail in the pull request.

---

# Source: `PROJECT_SCOPE.md`

# My-AI Product Scope

## In scope

- Local-first chat with persistent memory.
- Curriculum-based learning and evidence-backed skills.
- Coding, project tooling and sandboxed execution.
- Read-only database inspection/query analysis.
- Local files and multimodal inspection.
- Voice adapters for offline STT/TTS.
- Authorized security analysis.
- GitHub integration behind explicit permissions.
- Scheduler/resource controls, diagnostics, backup and recovery.
- Tested self-repair proposals and deny-by-default self-update.

## Explicitly out of scope

- Autonomous destructive actions.
- Arbitrary writes outside approved workspace/tool policies.
- Silent privilege escalation.
- External security operations without authorization and policy checks.
- Treating model output as proof of execution or verification.
- Adding a new product subsystem solely because an LLM suggested it.

## Change control

A new capability must define:
1. owner module and API boundary;
2. permission class;
3. read/write/execute behavior;
4. audit requirements;
5. regression tests;
6. documentation;
7. resource and failure limits.

This scope is the feature-creep guardrail for the project.

---

# Source: `PROJECT_STATUS.md`

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

---

# Source: `SECURITY.md`

# Security Policy

## Reporting

Do not disclose credentials, tokens, private repository contents, or exploitable details in public issues.
For a suspected security vulnerability, provide a minimal reproduction, affected component, impact, and the first known version/commit to the project maintainers through a private channel.

## Security boundaries

My-AI treats authentication, tool permissions, file confinement, code execution, external security analysis, backups, self-repair and self-update as security-sensitive surfaces.
Self-update is deny-by-default. A diagnostic result or generated patch is not authorization to activate it.

## Supported versions

Security fixes should target the current `main` branch unless a maintained release policy is explicitly established.

---

# Source: `docs/ARCHITECTURE.md`

# My-AI Architecture

## Runtime layers

1. API/UI — FastAPI routes, authentication, static UI and streaming.
2. Application — use-case composition and dependency injection.
3. Domain — pure intent/business decisions with no infrastructure imports.
4. Core — protocols and stable contracts.
5. Infrastructure — LLM, persistence and host/network adapters.
6. Capabilities — learning, memory, coding, files, voice, GitHub and security services.
7. Execution — sandboxed Python/project tooling and the remote executor service.
8. Maintenance — diagnostics, self-repair proposals and deny-by-default self-update.

## Request flow

HTTP request -> authentication -> central access policy -> application service -> domain/capability -> persistence -> audit

Chat follows:

message -> history/attachments -> application router service -> domain structured intent -> policy -> hybrid memory retrieval -> selected LLM -> response

The router is advisory and never grants permission.

## Dependency rules

- Domain imports only core contracts and standard-library code.
- Application depends on domain/core and injects infrastructure adapters through protocols.
- Infrastructure never depends on application or API layers.
- API is the composition/transport boundary and may call application services and capabilities.
- Legacy top-level router.py, llm.py and db.py are compatibility facades only.
- tests/test_architecture_boundaries.py statically enforces these rules on every CI run.

## Structured routing

Routing is provider-backed structured output with a strict JSON Schema. Ollama uses its schema-constrained format; OpenAI-compatible Responses uses strict text.format.type=json_schema. No keyword/regex classifier or free-form JSON fallback is used.

## Security boundaries

- File paths are resolved and constrained to approved roots.
- SQL integrations expose read-only query validation.
- Code execution is sandboxed/remote when configured.
- External security operations are policy constrained.
- Self-update is deny-by-default and requires isolated tests, approval, snapshot and health/rollback supervision.

---

# Source: `docs/FUTURE_ARCHITECTURE_ROADMAP.md`

# Future Architecture & Capability Roadmap

این سند roadmap توسعه پیشرفته My-AI است. در هر مرحله implementation باید با تست، benchmark و evidence همراه باشد.

## وضعیت اجرا

### Implemented foundation — 2026-10-01
- Model Router پایه با محدودیت RAM/VRAM/context/capability
- Context Budget Manager قطعی و قابل تست
- Capability Registry
- Policy/Permission Engine با approval برای عملیات حساس و online
- Runtime modes: offline/local/online
- Knowledge Version Store
- Evidence Store و conflict detection پایه
- Evidence/Trace Graph
- Resource Scheduler
- Evidence-based Completion Report
- Evaluation Harness با latency و failure reporting
- Regression tests برای تمام primitiveهای بالا

این foundation عمداً dependency-light است تا روی سخت‌افزار محدود نیز قابل اجرا باشد. این موارد فعلاً به‌صورت primitives مستقل اضافه شده‌اند و ادغام کامل هر primitive در همه مسیرهای runtime باید در مراحل بعدی با regression benchmark انجام شود.

## 1. Model Router
- انتخاب مدل بر اساس complexity، context، capability و RAM/VRAM
- fallback و ثبت دلیل انتخاب
- مدل سبک برای کارهای ساده و مدل قوی‌تر برای کارهای پیچیده
- ادغام کامل با provider lifecycle

## 2. Context Budget Manager
- token budget واقعی متناسب با model
- اولویت current request، state، evidence و relevant history
- summarization و compaction
- جلوگیری از context overflow

## 3. Knowledge Versioning
- نسخه‌بندی knowledge/research/decisions
- provenance، rollback و superseded state
- lifecycle و freshness

## 4. Conflict Resolution
- تشخیص conflict
- مقایسه source/version/freshness/confidence
- resolution قابل توضیح
- حفظ evidence متناقض بدون مخلوط‌کردن آن‌ها

## 5. Evidence Graph
requirement → research → source → claim → decision → artifact → validation را traceable نگه می‌دارد.

## 6. Automatic Regression Knowledge Tests
- queryهای مرجع
- precision/recall/ranking
- isolation و conflict tests
- اجرای CI

## 7. Categorized Long-Term Memory
- User Preferences
- Project Facts
- Technical Decisions
- Lessons Learned
- Research Evidence
- Known Failures
- Successful Patterns
- Temporary Context

## 8. Resource-Aware Scheduler
- CPU/RAM/VRAM awareness
- concurrency limits
- interactive priority
- background maintenance

## 9. Offline / Local / Online Modes
هر mode باید policy، permission و fallback مستقل داشته باشد.

## 10. Personal Benchmark
Benchmark برای conversation، coding، retrieval، planning، tools، repair، research، conflict و resource-awareness.

## 11. Semantic Retrieval Evolution
FTS5 → lexical ranking → local embeddings → semantic similarity → hybrid scoring → reranking → provenance/confidence-aware ranking.

## 12. Knowledge Freshness & Maintenance
scheduled re-validation، archive، superseded state و research مجدد برای knowledge مهم.

## 13. Evaluation Harness
- scenario evaluation
- regression detection
- latency/resource metrics
- failure classification
- model/provider comparison

## 14. Resource-Aware Model Selection
Model Router و Scheduler باید یک policy مشترک برای model/context/concurrency/timeout/fallback داشته باشند.

## 15. Evidence-Based Completion
هیچ success claim بدون validation evidence؛ گزارش باید goal، requirements، acceptance criteria، artifacts، research، tests و limitations را پوشش دهد.

## 16. Capability Registry
هر capability باید availability، permission، platform constraints، validation، risk و fallback داشته باشد.

## 17. Policy & Permission Layer
least privilege، approval، audit، project-level permission، online control و sandboxing.

## 18. Secure Self-Update
inspect → diagnose → proposal → approval → snapshot → isolated worktree → implementation → validation → activation → health check → rollback.

## 19. Personal Learning Loop
lesson extraction → validation → provenance → regression test → lifecycle/retirement.

## 20. Research-to-Code Traceability
requirement → query → source → finding → decision → implementation → validation.

## 21. Multi-Session & Backup
session isolation، persistent state، backup/restore، export/import و crash recovery.

## 22. Knowledge Management UI
search/filter، provenance، confidence، version history، conflicts، archive/delete و retrieval inspection.

## 23. Model Management
model metadata، health، capability profile، context limit، resource profile، benchmark و fallback policy.

## 24. Personal Software-Agent Benchmark Suite
سناریوهای end-to-end برای Python، PHP، Web، MQL4/MQL5، repair، wording variation، conflicts، missing tools، failed tests، research و offline-only.

## اولویت بعدی
1. ادغام Model Router و Resource Scheduler در runtime واقعی
2. Context Budget واقعی بر اساس context window مدل
3. Knowledge Versioning/Conflict به storage اصلی
4. Evaluation Harness مرکزی و benchmark dataset
5. Evidence Graph در execution trace
6. Freshness/maintenance
7. completion/traceability
8. multi-session/backup
9. management UI
10. model management
11. learning loop
12. secure self-update و benchmarkهای end-to-end

## اصل اجرایی
هر قابلیت جدید باید design، acceptance criteria، test/benchmark، failure handling، provenance و evidence موفقیت داشته باشد. قابلیت‌های جدید نباید با trigger-wordهای brittle جایگزین semantic reasoning شوند.

## وضعیت تکمیل معماری — 2026-10-01

تمام 24 محور roadmap اکنون دارای implementation یا integration عملی در runtime هستند:

| محور | implementation |
|---|---|
| 1 Model Router | persistent runtime selection + agent integration |
| 2 Context Budget | budget + context-window-aware packing |
| 3 Knowledge Versioning | knowledge_versions + version history API |
| 4 Conflict Resolution | conflict records + explicit resolution |
| 5 Evidence Graph | persistent nodes/edges |
| 6 Regression Knowledge Tests | retrieval regressions + roadmap tests |
| 7 Categorized Memory | knowledge categories + learning lessons |
| 8 Resource Scheduler | shared runtime scheduler |
| 9 Runtime Modes | offline/local/online authorization |
| 10 Personal Benchmark | persistent benchmark cases/results |
| 11 Semantic Retrieval | hybrid retrieval + candidate validation |
| 12 Freshness | scheduled maintenance/review records |
| 13 Evaluation Harness | evaluation primitive + persistent reports |
| 14 Resource-Aware Selection | RAM/VRAM/context/capability selection |
| 15 Evidence Completion | completion report with validation/limitations |
| 16 Capability Registry | persistent capability registry |
| 17 Policy Layer | approval + online permission boundary |
| 18 Secure Self-Update | snapshot/worktree/validation/watchdog/rollback |
| 19 Personal Learning Loop | lessons with provenance/regression case |
| 20 Research-to-Code | persistent research_trace |
| 21 Multi-Session & Backup | session isolation + existing backup/restore preserved |
| 22 Knowledge UI | roadmap knowledge management page |
| 23 Model Management | model/resource APIs and management page |
| 24 Agent Benchmark Suite | personal_agent_suite.json |

### Runtime acceptance surface

Roadmap APIs cover profile, model selection, resources, capabilities/authorization, knowledge versions/conflicts, evidence graph, execution trace, maintenance, lessons, research trace, completion reports and benchmark reporting.

این لایه‌ها additive هستند و storage دانش، conversation و backup موجود را حذف یا بازنویسی نمی‌کنند.

## Gap closure audit — 2026-10-01

بازبینی implementation نشان داد که چند مورد در جدول قبلی فقط به‌صورت primitive یا API بودند و ادغام runtime آن‌ها ناقص بود. این موارد اکنون تکمیل شده‌اند:

- **Context compaction:** در ContextBudgetManager فشرده‌سازی deterministic زیر فشار budget اضافه شد؛ داده‌های high-priority حفظ می‌شوند.
- **Evidence Graph runtime:** درخواست، model decision و knowledge provenance در مسیر chat/stream به node/edgeهای پایدار متصل می‌شوند.
- **Research-to-Code runtime:** اجرای software agent، sourceهای research را به requirement و artifact در research_trace و evidence graph متصل می‌کند.
- **Resource-aware maintenance:** maintenance با همان scheduler مشترک اجرا می‌شود و در زمان اشغال interactive slot به‌جای رقابت، deferred می‌شود.
- **Scheduled freshness:** maintenance به lifecycle برنامه اضافه شد و به‌صورت دوره‌ای در runtime اجرا می‌شود؛ archive همچنان explicit و non-destructive است.
- **Capability metadata:** platform constraints، validation و fallback برای capabilityها در storage و API قابل ثبت هستند.
- **Conflict inspection:** علاوه بر resolution، دو نسخه، source و confidence قابل مقایسه و inspection هستند.
- **Learning lifecycle:** lessonها lifecycle صریح candidate → validated → retired دارند.
- **Model management:** resource-fit/health profile و model-selection benchmark در runtime/API اضافه شدند.
- **Personal benchmark execution:** suite علاوه بر schema validation، runner اجرایی برای retrieval، toolchain readiness، resilience و traceability دارد و سناریوهای قابل اجرای local را واقعاً اجرا می‌کند؛ وابستگی‌های واقعی به compiler/LLM/browser با blocked و دلیل محیطی گزارش می‌شوند.
- **Knowledge management UI/API:** inventory/search، category filtering، archive، version history و retrieval inspection در سطح roadmap اضافه شدند.
- **Roadmap API security:** تمام endpointهای roadmap زیر احراز هویت موجود برنامه قرار گرفتند.

موارد زیر عمداً destructive/automatic نشده‌اند: حذف خودکار knowledge، بازنویسی backup، و activation خودکار self-update بدون approval. این‌ها مطابق اصل local-first و حفاظت از داده باقی می‌مانند.


### تکمیل audit نهایی — 2026-10-01
- **Knowledge rollback:** نسخه فعال knowledge اکنون قابل restore است و conflict resolution نیز نسخه انتخاب‌شده را به‌صورت پایدار فعال می‌کند؛ محتوای رکورد اصلی knowledge با نسخه انتخاب‌شده همگام می‌شود.
- **Research trace identity:** شناسه requirement در research-to-code با SHA-256 پایدار شده تا بین processها و اجراهای جداگانه قابل ردیابی بماند.
- **Maintenance failure safety:** حتی در خطای fetch اولیه نیز scheduler slot در مسیر finally آزاد می‌شود.
- **Context compaction:** budgetهای کوچک نیز با compaction قطعی مدیریت می‌شوند و regression test مستقل دارند.

مواردی که به ابزار خارجی وابسته‌اند (برای نمونه اجرای واقعی MQL compiler یا live LLM/browser) به‌جای success جعلی، با وضعیت blocked و دلیل محیطی گزارش می‌شوند؛ سایر سناریوهای قابل اجرای local در runner واقعاً اجرا و نتیجه‌گذاری می‌شوند.

---

# Source: `docs/GENERAL_SOFTWARE_AGENT.md`

# General Software Engineering Agent

## هدف

My-AI باید یک درخواست نرم‌افزاری را مستقل از واژه‌های ثابت درک کند، درباره فناوری‌ها و محدودیت‌های واقعی تحقیق کند، از دانش محلی و منابع وب استفاده کند، نوع artifact و قابلیت‌های قابل‌اجرا را مشخص کند، معماری و برنامه اجرا بسازد، پروژه را پیاده‌سازی و اعتبارسنجی کند، خطاها را تحلیل و اصلاح کند و فقط وقتی معیارهای اتمام برآورده شدند نتیجه را کامل اعلام کند.

## چرخه استاندارد

```text
درخواست آزاد کاربر
  ↓
Semantic Understanding + Conversation Context
  ↓
Artifact / Capability Identification
  ↓
Requirements + Constraints + Acceptance Criteria
  ↓
Local Knowledge Retrieval + Web Research
  ↓
Platform Capability / Compatibility Check
  ↓
Architecture + Technology Decision
  ↓
Implementation Plan
  ↓
Generate / Modify Project
  ↓
Semantic Artifact Validation
  ↓
Build / Run
  ↓
Tests / Lint / Type / API / Browser / Runtime validation
  ↓
Failure diagnosis
  ├── requirement ambiguity → resolve from context or ask only when essential
  ├── missing knowledge → research again
  ├── platform conflict → redesign valid architecture
  └── implementation failure → repair
  ↓
Re-test
  ↓
Self-review against requirements
  ↓
Cleanup
  ↓
Git status / diff / commit
  ↓
Final evidence-based completion report
```

## Semantic understanding

Router و Planner نباید برای تشخیص عملیات به فهرست trigger word وابسته باشند. عبارت‌های متفاوتی مانند درخواست مستقیم، غیرمستقیم، محاوره‌ای یا ادامه یک کار باید بر اساس معنی یکسان resolve شوند. current user request اولویت دارد و تاریخچه فقط برای resolve کردن reference و حفظ هدف پروژه استفاده می‌شود.

## Artifact و قابلیت

قبل از تولید کد، Planner باید مشخص کند کاربر چه چیزی می‌خواهد بسازد: application، website، API، library، CLI، mobile app، indicator، expert advisor، script یا نوع دیگری از artifact. سپس باید بررسی کند که قابلیت‌های درخواستی واقعاً توسط آن artifact و platform قابل انجام هستند یا نه.

اگر دو requirement با محدودیت platform متعارض باشند، Agent نباید کد جعلی تولید کند یا یک capability را با placeholder شبیه‌سازی کند. باید از تحقیق و documentation برای تعیین محدودیت استفاده کند و نزدیک‌ترین معماری معتبر را انتخاب کند؛ در صورت نیاز artifact را به چند جزء سازگار تقسیم کند.

## تحقیق

تحقیق از دانش داخلی و WebLearner انجام می‌شود. برای مسائل تخصصی، research queries باید API رسمی، محدودیت platform، compatibility، syntax، نسخه و روش validation را پوشش دهند. منابع و خلاصه آن‌ها در project context ثبت می‌شوند تا تصمیم فنی قابل ردیابی باشد.

## Planner

Plan ساختاریافته باید حداقل شامل این موارد باشد:

- goal
- artifact_type
- language/framework
- requirements
- architecture
- phases
- acceptance_criteria
- research_queries
- validation strategy
- constraints
- ambiguities

Planner نباید قبل از تحقیق یک capability نامطمئن را قطعی فرض کند.

## Implementation و validation

Generator باید کل artifact قابل اجرا را تولید کند، نه فقط یک snippet. پس از تولید، یک semantic validation مستقل از compiler بررسی می‌کند که artifact با plan و platform سازگار است و placeholder یا API ناسازگار ندارد. سپس compiler/runtime/test/lint اجرا می‌شوند.

مثال: اگر کاربر artifact نوع custom indicator برای یک platform درخواست کند ولی یک عملیات فقط در expert advisor/script مجاز باشد، Agent نباید صرفاً نام indicator را روی یک EA با API اشتباه بگذارد. باید محدودیت را تشخیص دهد و architecture معتبر ارائه کند.

## Validation matrix

- Python: compile، pytest، lint و type checking در صورت وجود ابزار
- Rust: cargo check/test/clippy
- JavaScript/TypeScript: install، build، test، lint و browser E2E برای وب
- PHP: syntax، test، lint و framework test suite در صورت وجود
- SQL: schema/migration و integration validation
- Android/iOS: build و testهای موجود در محیط توسعه
- MQL4/MQL5: compiler/toolchain واقعی؛ نبود compiler باید blocked/incomplete گزارش شود
- Web: backend/API + browser/runtime validation
- CLI/Desktop: اجرای سناریوهای functional متناسب با artifact

## Repair loop

هر failure باید diagnosis شود و همان validation شکست‌خورده دوباره اجرا شود. در صورت نیاز Agent باید research را تکرار کند. تعداد repairها محدود است، اما پایان repair loop با خطا هرگز success محسوب نمی‌شود.

## Self-review و Git

پیش از completion، requirements، acceptance criteria، placeholderها، dependencyهای غیرضروری، فایل‌های موقت و runtime state بررسی می‌شوند. Git فقط برای workspace پروژه تولیدشده استفاده می‌شود و commit نهایی تنها پس از validation انجام می‌شود.

## معیار اتمام

`completed` فقط وقتی مجاز است که:

1. هدف و artifact موردنظر resolve شده باشد.
2. plan، requirements و acceptance criteria وجود داشته باشد.
3. research موردنیاز انجام شده باشد یا دلیل مستند برای عدم دسترسی وجود داشته باشد.
4. artifactهای لازم تولید شده باشند.
5. semantic validation موفق باشد.
6. build/test/lint/runtime validation متناسب با پروژه موفق باشد یا صریحاً blocked گزارش شود.
7. failure حل‌نشده وجود نداشته باشد.
8. self-review انجام شده باشد.
9. مسیر workspace و وضعیت Git مشخص باشد.

`generated`، `files_created` یا `build_passed` به‌تنهایی به معنی `completed` نیستند.

## سناریوهای پذیرش

1. درخواست آزاد برای یک بازی Python و بررسی ساخت، اجرا و تست.
2. درخواست آزاد برای یک پروژه PHP و بررسی dependency، syntax، test و run.
3. درخواست آزاد برای یک وب‌سایت چندبخشی و بررسی build/API/browser.
4. درخواست آزاد برای یک artifact MQL4 و بررسی تشخیص artifact، تحقیق platform، تولید `.mq4` و compilation واقعی در صورت تنظیم MetaEditor.
5. ادامه همان پروژه با جمله‌ای کاملاً متفاوت از درخواست قبلی.
6. اصلاح پروژه موجود بدون ساختن پروژه نامرتبط جدید.
7. درخواست دارای دو قابلیت متعارض و بررسی اینکه Agent به‌جای تولید کد جعلی، محدودیت را تشخیص داده و معماری معتبر انتخاب می‌کند.

---

# Source: `docs/help/api.md`

# API

مستندات تعاملی API در `/docs` و `/redoc` قرار دارند.

## یادگیری

```
GET  /learning
GET  /learning/active
GET  /learning/catalog
GET  /learning/status
POST /learning/start
POST /learning/step
POST /learning/learn
POST /learning/practice
POST /learning/{language}/stop
POST /learning/{language}/resume
```

## Scheduler

```
POST /scheduler/start
GET  /scheduler/status
POST /scheduler/stop
GET  /scheduler/resources
```

## کاربران و دسترسی

احراز هویت، نقش‌ها و مجوزهای per-tool در Settings مدیریت می‌شوند. مجوزهای عملیاتی سه سطح دارند:

- `read`
- `write`
- `execute`

ابزارهای حساس مانند GitHub write، امنیت، database، code execution، self-update و self-repair باید طبق permission کاربر و سیاست فرمان اجازه داشته باشند.

## فایل و چندرسانه‌ای

```
GET  /files/roots
GET  /files/list
POST /files/inspect
POST /files/read
POST /files/upload
POST /files/analyze
POST /files/prerequisites
POST /files/generate/docx
POST /files/generate/xlsx
POST /files/generate/pdf
POST /files/generate/pptx
```

---

# Source: `docs/help/chat.md`

# راهنمای چت و گفتگو

## استفاده
- برای شروع گفتگو پیام را در کادر دستور وارد کنید.
- Enter برای ارسال است؛ Ctrl+Enter و Shift+Enter برای شکستن خط استفاده می‌شود.
- گفتگوها در بخش «چت‌های اخیر» ذخیره می‌شوند و قابل تغییرنام، پین و حذف هستند.

## پرسیدن از My-AI
در هر موضوع می‌توانید بنویسید: «راهنمای این بخش را توضیح بده». اگر راهنمای محلی کافی نباشد، My-AI می‌تواند مستندات آنلاین را بررسی کند و فقط با تأیید شما پیشنهاد را در راهنمای محلی ثبت کند.