# My-AI — Local Personal AI Assistant

My-AI is a **local-first personal AI assistant** built around Ollama, FastAPI and SQLite. It combines chat, persistent memory, continuous learning, project generation, code execution, security testing, Git/GitHub integration, documentation help, voice, local-file processing, resource control, self-update and self-repair.

این پروژه یک دستیار هوش مصنوعی **local-first** است که هسته مدل آن با Ollama اجرا می‌شود و امکاناتی مانند چت، حافظه پایدار، یادگیری مداوم، تولید کد و پروژه، اجرای کنترل‌شده کد، بررسی امنیت، Git/GitHub، راهنمای داخلی، Voice، پردازش فایل، کنترل منابع، self-update و self-repair را فراهم می‌کند.

> **Documentation goal:** this README intentionally contains a complete feature/module inventory so missing or unfinished areas can be identified before further development.
>
> **هدف این مستند:** این README عمداً فهرست کامل قابلیت‌ها و ماژول‌های موجود را ثبت می‌کند تا بخش‌های فراموش‌شده یا ناقص قبل از توسعه بعدی مشخص شوند.

---

# فارسی — فهرست کامل قابلیت‌ها و ماژول‌ها

## 1. هسته دستیار، Agent و Chat

- اجرای مدل محلی از طریق Ollama.
- Command Router برای تشخیص نوع درخواست.
- Agent برای هماهنگ‌کردن Chat، Learning، Code، Project، Security، Help و Git.
- پاسخ context-aware با استفاده از مکالمه و حافظه پایدار.
- پشتیبانی از فارسی و انگلیسی.
- تشخیص دستورات طبیعی مانند:
  - «پایتون یاد بگیر»
  - «برای من یک API بساز»
  - «این پروژه را تست امنیتی کن»
  - «GitHub را بررسی کن»
  - «این فایل را تحلیل کن»
  - «برایم Word/Excel/PDF/PowerPoint بساز»
- رابط وب برای Chat.
- ارسال فایل از داخل Chat و اتصال فایل به پیام/تحلیل.

## 2. مدل‌های LLM و تنظیمات Ollama

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `ROUTER_MODEL`
- `CODING_MODEL`
- `FALLBACK_MODEL`
- `EMBEDDING_MODEL`
- `OLLAMA_NUM_CTX`
- `OLLAMA_NUM_THREAD`
- `OLLAMA_KEEP_ALIVE`
- پشتیبانی از اجرای CPU-only.
- GPU اختیاری است و مقدار پیش‌فرض GPU layers برابر صفر است.

## 3. حافظه پایدار

ماژول‌های مرتبط: `db.py`, `memory.py`, `metrics.py`

ذخیره‌سازی SQLite شامل:

- conversations
- knowledge
- learning sessions
- experiments
- project tasks
- generated projects
- security scans
- help updates
- audit records
- authentication sessions
- user/tool permissions
- settings

قابلیت‌ها:

- جست‌وجوی FTS5.
- بازیابی دانش مرتبط برای پاسخ و تولید کد.
- نگهداری وضعیت پروژه و یادگیری.
- ثبت رخدادها و audit.

Endpointهای اصلی:

```text
GET /memory/knowledge
GET /memory/search?q=python&limit=8
```

## 4. یادگیری مداوم و Curriculum

ماژول‌های مرتبط: `learner.py`, `dynamic_learning.py`, `curriculum.py`, `advanced_curriculum.py`, `forex_curriculum.py`, `learning_resilience.py`, `scheduler.py`

Pipeline یادگیری:

```text
Curriculum
  ↓
Topic selection
  ↓
Reference/source retrieval
  ↓
Local LLM extraction
  ↓
Persistent SQLite knowledge
  ↓
Lesson + examples + exercises + checklist
  ↓
Assessment
  ↓
Progress
  ↓
Next topic
```

ویژگی‌ها:

- انتخاب موضوع بعدی.
- دریافت منابع مرجع.
- استخراج دانش با مدل محلی.
- ذخیره منبع و یادداشت.
- ساخت درس.
- مثال و تمرین.
- checklist.
- ارزیابی.
- ثبت نمره و پیشرفت.
- اجرای چند مسیر یادگیری به‌صورت مستقل.
- ادامه یادگیری در background.
- توقف و ادامه یادگیری.
- نمایش وضعیت runtime.
- کنترل منابع هنگام یادگیری.
- retry با backoff برای خطاهای موقت.
- خطای موقت نباید صرفاً به دلیل رسیدن به یک سقف retry محدود، learning طولانی‌مدت را دائماً متوقف کند.

### مسیرهای برنامه‌نویسی و فنی

- Rust — از پایه تا مباحث expert شامل ownership، borrowing، lifetimes، async، unsafe، FFI، performance، security، production و capstone.
- Python
- C
- PHP
- JavaScript
- SQL Server / T-SQL
- MySQL
- SQLite
- Android / Kotlin
- iOS / Swift
- Pentest / Security Testing
- Forex

### Forex curriculum

مسیر Forex دارای **121 موضوع صریح** است و موضوعات حرفه‌ای سرمایه/ریسک و capstone مربوط به Forex/MetaTrader را نیز شامل می‌شود.

منابع آن شامل مستندات MetaTrader، MQL4/MQL5، منابع آموزشی Forex و منابع آموزشی CME/Investopedia است.

### منابع تکمیلی اختصاصی هر سرفصل

هر سرفصل فقط از فهرست عمومی منابع domain استفاده نمی‌کند. برای هر topic، My-AI یک مجموعه منبع تکمیلی topic-specific انتخاب می‌کند و آن را قبل از منابع عمومی وارد pipeline یادگیری می‌کند.

- منابع رسمی و منابع تکمیلی از هم تفکیک شده‌اند.
- هر topic حداقل دو منبع تکمیلی دارد.
- منابع تکمیلی بر اساس موضوع انتخاب می‌شوند؛ مانند async، testing، security، performance، database، MQL4/MQL5، technical analysis و risk management.
- review هفتگی نیز منابع تکمیلی topicها را بررسی می‌کند تا به‌روزرسانی curriculum فقط به مستندات عمومی وابسته نباشد.
- برای Forex، پوشش منابع تکمیلی روی کل curriculum موجود، شامل مباحث تکنیکال، مدیریت ریسک، backtesting، MQL4/MQL5، MetaTrader و research/production نیز اعمال می‌شود.



### Pentest learning

Pentest یک مسیر مستقل از PHP است و شامل:

- Security fundamentals
- Linux
- networking
- web security
- API security
- reconnaissance
- asset discovery
- vulnerability assessment
- code review
- security tooling
- reporting
- authorized project testing

## 5. کنترل Learning

قابلیت‌های UI/API:

- مشاهده مسیرهای فعال.
- دکمه **متوقف کردن یادگیری**.
- دکمه **ادامه یادگیری**.
- مشاهده progress هر مسیر.
- مشاهده phase و topic جاری.
- اجرای چند مسیر مستقل.
- scheduler جداگانه برای مسیرها.

Endpointهای مرتبط:

```text
GET  /learning
GET  /learning/active
GET  /learning/catalog
GET  /learning/status
POST /learning/{language}/stop
POST /learning/{language}/resume
POST /learning/start
POST /learning/step
POST /learning/learn
POST /learning/practice
```

## 6. Custom Courses

ماژول: `settings_feature.py`

ادمین می‌تواند curriculum سفارشی ایجاد کند.

امکانات:

- ساخت course جدید.
- description برای course.
- تعریف topicهای دلخواه.
- تعریف goal برای هر topic.
- ثبت source URL برای topic.
- مشاهده progress.
- شروع/ادامه course.
- pause کردن course.

Endpointها:

```text
GET  /settings/courses
POST /settings/courses
GET  /settings/courses/{course_id}/progress
POST /settings/courses/{course_id}/start
POST /settings/courses/{course_id}/pause
POST /learning/{course_id}/start
```

## 6.1 Continuous Learning Review

After a domain is fully completed, My-AI schedules a review every **7 days**. The review reads the configured official and complementary reference set, checks current web evidence for real changes, deduplicates new material, appends genuinely new topics to the existing curriculum, and automatically starts learning the new topics. The main dashboard shows the new worker and its live status.

Manual **Stop** disables automatic restart for that learning domain; **Resume** re-enables it.

Reference sets are domain-specific and include primary documentation plus ecosystem documentation, standards, release notes, security, testing, performance, tooling and production references where applicable. Python includes the official Python documentation, PyPA packaging documentation, PEPs and the Python Developer Guide. The official Python documentation itself notes that its tutorial is not intended to cover every feature, which is why the broader source set is used.

## 7. Scheduler و اجرای background

ماژول: `scheduler.py`

- اجرای learning در background.
- worker مستقل برای مسیرهای مختلف.
- امکان اجرای هم‌زمان چند موضوع/زبان.
- Chat هنگام learning قفل نمی‌شود.
- status runtime.
- start/stop scheduler.
- interval از 60 ثانیه تا 24 ساعت.
- توقف graceful با stop event.
- resource-aware waiting.
- retry با exponential backoff تا سقف delay عملیاتی.

Endpointها:

```text
POST /scheduler/start
GET  /scheduler/status
POST /scheduler/stop
```

## 8. Resource Control

ماژول‌ها: `resource_guard.py`, `settings_store.py`

تنظیمات قابل تغییر و persistent:

| گزینه | مقدار پیش‌فرض |
|---|---:|
| CPU max | 70% |
| CPU threads | 8 |
| RAM max | 80% |
| GPU layers | 0 |

- خواندن live تنظیمات از SQLite.
- worker قبل از شروع واحد یادگیری مصرف CPU/RAM را بررسی می‌کند.
- اگر مصرف از سقف تنظیم‌شده بیشتر باشد worker منتظر می‌ماند.
- GPU اختیاری است.
- CPU-only مسیر پیش‌فرض است.

## 9. Settings و مدیریت پیکربندی

ماژول‌ها: `settings_feature.py`, `settings_store.py`, `settings_script.js`

بخش Settings شامل:

### GitHub

- API URL
- repository
- username
- token configuration
- token verification
- GitHub Enterprise API URL
- login/logout/check

### Self-update

- enable/disable
- explicit approval
- local health URL

### Self-repair

- enable/disable
- require approval

### Learning

- fast learning option
- learning interval
- retry configuration

### Resources

- CPU percent
- CPU threads
- RAM percent
- GPU layers

### Users

- مشاهده کاربران
- ایجاد کاربر
- فعال/غیرفعال کردن کاربر
- role

### Tool permissions

برای هر کاربر و tool می‌توان actionهای زیر را کنترل کرد:

- read
- write
- execute

Toolهای قابل مدیریت در UI شامل:

```text
chat
code-generation
code-execution
learning
scheduler
github
security
database
voice
models
memory
web
projects
eval
self-update
self-repair
help
tools
```

## 10. Authentication و Authorization

ماژول: `auth.py`

- user account.
- اولین account به‌صورت admin ایجاد می‌شود.
- password با `scrypt` hash می‌شود.
- salt تصادفی.
- session token امن.
- session expiration برابر 24 ساعت.
- logout/revoke session.
- user role: admin/user.
- `require_user` برای مسیرهای نیازمند ورود.
- `require_admin` برای تنظیمات حساس.
- per-tool permission برای کاربران عادی.
- audit log برای عملیات.

## 11. Code Generation

ماژول‌های مرتبط: `agent.py`, `llm.py`, `tooling.py`, `project_workspace.py`

قابلیت‌ها:

- تبدیل هدف کاربر به task.
- acceptance criteria.
- بازیابی دانش مرتبط از memory.
- تولید کد.
- اصلاح کد.
- ایجاد پروژه.
- ثبت وضعیت پروژه.
- تولید پروژه در workspace جداگانه.

نمونه:

```text
برای من یک API مدیریت کاربران با Python بساز
یک پروژه PHP برای مدیریت کاربران بساز
یک برنامه JavaScript بنویس
```

## 12. Project Planning و Workspace

ماژول‌ها: `project_workspace.py`, `tooling.py`

- project plan.
- task generation.
- acceptance criteria.
- project task tracking.
- generated-project memory.
- workspace مستقل برای هر پروژه.
- `projects/` برای پروژه‌های runtime.
- جلوگیری از اجرای toolهای پروژه خارج از workspace تعریف‌شده.

Endpointها:

```text
POST /projects/plan
GET  /projects/tasks
POST /tools/project
```

## 13. Toolchain

ماژول: `tooling.py`

برای مسیرهای زیر تشخیص toolchain و عملیات توسعه وجود دارد:

- Python
- C
- PHP
- JavaScript
- Rust
- Kotlin
- Swift
- Android
- iOS

عملیات پشتیبانی‌شده بسته به toolchain:

- detect
- build
- lint
- test
- project operations

این ابزارها shell آزاد و unrestricted در اختیار مدل قرار نمی‌دهند و به workspace پروژه محدود هستند.

Endpointها:

```text
GET  /tools/catalog
GET  /tools/doctor
POST /tools/project
```

## 14. Python Executor و Sandbox

ماژول‌ها: `executor.py`, `executor_service.py`

حالت پیش‌فرض: **Container Executor**.

ویژگی‌های isolation:

- Docker container.
- `--network none`.
- host filesystem به‌صورت read-only.
- حذف capabilityها.
- `no-new-privileges`.
- محدودیت RAM.
- محدودیت CPU.
- محدودیت PID.
- timeout.
- output limit.
- حذف container بعد از اجرا.

تنظیمات:

```text
EXEC_TIMEOUT
EXECUTOR_MODE
EXECUTOR_IMAGE
EXEC_MEMORY
EXEC_CPUS
EXEC_PIDS
EXEC_OUTPUT_CHARS
```

حالت جایگزین:

```text
EXECUTOR_MODE=subprocess
```

این حالت isolation کمتری دارد و برای کد کاملاً غیرقابل‌اعتماد مناسب نیست.

Endpoint:

```text
POST /code/run
POST /tools/python
```

## 15. SQL Server و SQLite

ماژول‌های مرتبط: `tooling.py`, `db.py`

### SQL Server

- schema inspection فقط‌خواندنی.
- query فقط‌خواندنی.
- پشتیبانی از driver رسمی Microsoft `mssql-python`.
- connection string از:

```text
MYAI_SQLSERVER_CONNECTION_STRING
```

### SQLite

- schema inspection.
- query read-only.
- ریشه مجاز برای SQLite خارجی با:

```text
MYAI_SQLITE_ROOT
```

Endpointها:

```text
GET  /tools/sqlserver/schema
POST /tools/sqlserver/query
GET  /tools/sqlite/schema
POST /tools/sqlite/query
```

## 16. Security Static Analysis

ماژول: `security.py`

بررسی‌های static/source شامل:

- secrets
- eval/exec
- shell execution
- weak hashes
- SQL injection patterns
- debug mode
- unsafe CORS
- DOM sinks
- path traversal
- plaintext passwords
- dependency manifests

Endpointها:

```text
POST /security/scan
GET  /security/history
```

## 17. DAST

ماژول: `dast.py`

قابلیت‌ها:

- اجرای پروژه محلی روی loopback.
- route discovery.
- HTTP request واقعی.
- security headers.
- HTTP 500 detection.
- debug/stack-trace leakage.
- reflection checks.
- TRACE.
- cookie flags.
- CSRF indicators.
- limited same-origin crawl.
- OpenAPI endpoint checks.

برای هدف خارجی:

- URL باید صریحاً توسط کاربر ارائه شود.
- مقصد باید عمومی باشد.
- تست باید مجاز باشد.
- external scan non-destructive است.
- remote code modification انجام نمی‌شود.

نمونه:

```text
پن‌تست آدرس: https://example.com
پن‌تست آدرس: https://example.com فقط گزارش بده
پن‌تست آدرس: https://example.com و باگ‌ها را اصلاح کن
```

## 18. سیاست تست و اصلاح

رفتار از متن صریح کاربر تعیین می‌شود:

```text
از پروژه تست بگیر
→ گزارش امنیتی، بدون اصلاح

پن‌تست بگیر و فقط گزارش بده
→ فقط گزارش

پن‌تست بگیر و باگ‌ها را رفع کن
→ تست، اصلاح و تست مجدد

فقط اشکالات را بگو
→ بدون تغییر فایل
```

## 19. Web Learning

ماژول‌ها: `web_learner.py`, `network.py`

- دریافت URL مشخص.
- استخراج محتوای صفحه.
- محدودیت متن استخراج‌شده با `MAX_WEB_CHARS`.
- استفاده از منابع رسمی/مرجع در بخش‌های شناخته‌شده.
- validation برای URL.
- کنترل redirect.
- DNS/IP validation.
- استفاده از DNS pinning برای درخواست‌های خارجی حساس.

Endpoint:

```text
POST /learn/url
```

## 20. Help و Documentation

ماژول: `help.py`

سیستم Help داخلی:

```text
GET  /help
POST /help/ask
GET  /help/updates
POST /help/approve/{update_id}
POST /help/reject/{update_id}
```

قابلیت‌ها:

- توضیح قابلیت‌های برنامه.
- راهنمای GitHub.
- راهنمای Docker.
- راهنمای Learning.
- راهنمای Security/Pentest.
- راهنمای تنظیمات.
- جست‌وجوی مستندات فعلی.
- مقایسه روش فعلی با مستندات جدید.
- ساخت پیشنهاد تغییر documentation.
- اعمال تغییر فقط پس از تأیید کاربر.
- جلوگیری از اعمال خودکار تغییر پیشنهادی.

## 21. Git و GitHub

ماژول: `git_connector.py`

### Read

- repository
- tree
- file
- issues
- pull requests
- branches

### Write

- create branch
- create/update file

نوشتن نیازمند:

```text
allow_write=true
```

و token با permission مناسب است.

Environment:

```text
GITHUB_TOKEN
GITHUB_API_URL
```

Endpointها:

```text
GET  /git/repo
GET  /git/tree
GET  /git/file
GET  /git/issues
GET  /git/pulls
GET  /git/branches
POST /git/branch
PUT  /git/file
GET  /git/check
POST /git/login
POST /git/logout
```

## 22. Local File Access و File Processing

ماژول‌ها: `local_files.py`, `file_processing.py`, `multimodal.py`, `feature_routes.py`

قابلیت‌های فایل:

- مشاهده rootهای قابل دسترسی.
- list فایل‌ها و پوشه‌ها.
- inspect فایل.
- read فایل.
- upload فایل به workspace برنامه.
- تحلیل فایل.
- ارسال فایل از Chat.
- تشخیص MIME/type.
- استخراج متن.
- استخراج DOCX.
- استخراج XLSX.
- استخراج PDF.
- metadata تصویر.
- تحلیل semantic تصویر با مدل vision در Ollama در صورت پشتیبانی مدل.
- metadata صوت و ویدئو با `ffprobe` در صورت نصب.
- تشخیص prerequisiteهای Python.

مسیرهای read/list/inspect/read ذاتاً read-only هستند.

نوشتن فایل توسط قابلیت‌های جدید فقط در عملیات صریح مانند upload/generation انجام می‌شود.

حداکثر upload فعلی: **100 MiB**.

Endpointها:

```text
GET  /files/roots
GET  /files/list?path=...
POST /files/inspect
POST /files/read
POST /files/upload
POST /files/analyze
POST /files/prerequisites
```

## 23. Prerequisite Management

برای انواع فایل شناخته‌شده، برنامه می‌تواند dependencyهای Python لازم را تشخیص دهد و در صورت نبودن، آن‌ها را با pip نصب کند.

پکیج‌های شناخته‌شده شامل:

- `python-docx`
- `openpyxl`
- `python-pptx`
- `PyMuPDF`
- `Pillow`

این مکانیزم به‌صورت allowlist شده برای dependencyهای شناخته‌شده عمل می‌کند و به‌معنی نصب خودکار هر نرم‌افزار سیستم‌عاملی نیست.

## 24. File Generation

قابلیت تولید:

- Word / DOCX
- Excel / XLSX
- PDF
- PowerPoint / PPTX

Endpointها:

```text
POST /files/generate/docx
POST /files/generate/xlsx
POST /files/generate/pdf
POST /files/generate/pptx
```

فایل‌های تولیدشده در workspace برنامه ذخیره می‌شوند و API مسیر فایل تولیدشده را برمی‌گرداند.

## 25. Multimodal

ماژول: `multimodal.py`

نوع‌های فعلی:

- text
- image
- DOCX
- XLSX
- PDF
- audio metadata
- video metadata
- unknown/binary inspection

تصویر می‌تواند با مدل vision در Ollama تحلیل معنایی شود.

برای audio/video در پیاده‌سازی فعلی، `ffprobe` برای metadata استفاده می‌شود و transcription/semantic analysis کامل وابسته به voice/transcription configuration است.

## 26. Voice

ماژول: `voice.py`

Browser APIs:

- `SpeechRecognition`
- `webkitSpeechRecognition`
- `speechSynthesis`

زبان‌ها:

```text
fa-IR
 en-US
```

Voice input به browser support و microphone permission وابسته است.

## 27. Backup / Restore و رمزنگاری

ماژول‌های مرتبط: `backup_crypto.py`, `config.py`, `db.py`

- backup/restore runtime data در root مجاز.
- محدودکردن backup/import/restore به مسیر safe root.
- پشتیبانی از رمزنگاری مرتبط با backup.
- root پیش‌فرض:

```text
MYAI_BACKUP_ROOT=data/backups
```

## 28. Self-update

ماژول: `self_update.py`

Workflow:

```text
Git state
 ↓
separate worktree
 ↓
test
 ↓
snapshot
 ↓
activation
 ↓
watchdog
 ↓
rollback on failure
```

- update در worktree جدا تست می‌شود.
- قبل از activation snapshot ساخته می‌شود.
- health check محلی.
- watchdog برای تشخیص شکست.
- rollback در صورت شکست.
- self-update health URL فقط باید به local host اشاره کند.

## 29. Self-repair

ماژول: `self_repair.py`

Workflow:

```text
Diagnose
 ↓
Collect previous lessons
 ↓
Generate unified patch
 ↓
Isolated worktree
 ↓
compileall + pytest
 ↓
Explicit user approval
 ↓
Apply patch
 ↓
Re-test
 ↓
Rollback on failure
```

- `self-repair/` workspace اختصاصی.
- `self-repair/lessons.jsonl` برای lessons.
- جدول `fix_attempts` برای feedback loop.
- lessons اخیر وارد prompt تولید patch می‌شوند.
- اعمال patch بدون approval صریح انجام نمی‌شود.

## 30. Watchdog

ماژول: `watchdog.py`

- health monitoring مربوط به update/activation.
- تشخیص failure.
- کمک به rollback.
- نگهداری artifactهای runtime در workspace مخصوص.

## 31. Network Security

ماژول: `network.py`

- URL validation.
- DNS resolution controls.
- public/private address checks.
- redirect validation.
- DNS pinning برای درخواست‌های خارجی حساس.
- حفظ hostname برای Host/SNI در کنار اتصال به IP انتخاب‌شده.

## 32. Platform Detection

ماژول: `platform.py`

- تشخیص platform/OS.
- abstraction برای تفاوت‌های Windows/Linux/macOS.
- کمک به انتخاب command/toolchain مناسب.

## 33. Capabilities و Skill Engine

ماژول‌ها: `capabilities.py`, `skill_engine.py`, `domain_registry.py`

- ثبت قابلیت‌های موجود.
- registry برای domainها.
- skillهای قابل تشخیص/اجرای داخلی.
- اتصال domain/skill به routing و agent.
- تفکیک capabilityها از implementation جزئی.

## 34. Command Policy

ماژول: `command_policy.py`

- بررسی سیاست اجرای command.
- محدودکردن عملیات خطرناک.
- تفکیک read/write/execute.
- اعمال policy قبل از اجرای toolهای حساس.

## 35. Metrics و Observability

ماژول: `metrics.py`

- ثبت/محاسبه metricهای runtime.
- کمک به مشاهده وضعیت عملیات.
- نگهداری اطلاعات قابل استفاده برای diagnostics و testing.

## 36. Notifications

ماژول: `notifications.py`

- abstraction مربوط به notification/event messages.
- استفاده توسط بخش‌های runtime برای اطلاع‌رسانی وضعیت.

## 37. Audit و Decision Log

ماژول‌ها: `auth.py`, `decision_log.py`

- audit log برای عملیات حساس.
- ثبت user/tool/action/status/details.
- decision log برای ثبت تصمیمات داخلی مرتبط با workflow.

## 38. Web UI

ماژول‌ها: `ui.py`, `ui_extensions.py`

رابط کاربری شامل:

- Chat
- Learning dashboard
- Learning progress
- stop/resume learning
- Settings
- Help
- Voice
- file attachment
- file analysis
- bilingual layout

زبان‌ها:

- فارسی RTL
- English LTR

`ui_extensions.py` قابلیت‌های جدید را بدون نیاز به بازنویسی کامل UI اصلی به رابط تزریق می‌کند.

## 39. API / OpenAPI

FastAPI API documentation:

```text
/docs
/redoc
```

### API inventory

```text
POST /chat

POST /code/generate
POST /code/run

POST /security/scan
GET  /security/history

POST /learn/url

POST /learning/start
POST /learning/step
POST /learning/learn
GET  /learning/status
GET  /learning/active
GET  /learning/catalog
POST /learning/practice
POST /learning/{language}/stop
POST /learning/{language}/resume
POST /learning/{course_id}/start

POST /projects/plan
GET  /projects/tasks

GET  /memory/search
GET  /memory/knowledge

POST /scheduler/start
GET  /scheduler/status
POST /scheduler/stop

GET  /help
POST /help/ask
GET  /help/updates
POST /help/approve/{update_id}
POST /help/reject/{update_id}

GET  /git/repo
GET  /git/tree
GET  /git/file
GET  /git/issues
GET  /git/pulls
GET  /git/branches
POST /git/branch
PUT  /git/file
GET  /git/check
POST /git/login
POST /git/logout

GET  /tools/catalog
GET  /tools/doctor
POST /tools/project
POST /tools/python
GET  /tools/sqlserver/schema
POST /tools/sqlserver/query
GET  /tools/sqlite/schema
POST /tools/sqlite/query

GET  /settings
GET  /settings/config
PUT  /settings/github
POST /settings/github-token
GET  /settings/github
PUT  /settings/features
PUT  /settings/resources
GET  /settings/users
GET  /settings/tool-permissions
PUT  /settings/tool-permissions
GET  /settings/courses
POST /settings/courses
GET  /settings/courses/{course_id}/progress
POST /settings/courses/{course_id}/start
POST /settings/courses/{course_id}/pause
GET  /settings/script.js

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

## 40. Configuration Reference

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Default model |
| `ROUTER_MODEL` | `qwen2.5:7b` | Router model |
| `CODING_MODEL` | `qwen2.5:7b` | Coding model |
| `FALLBACK_MODEL` | `qwen2.5:7b` | Fallback model |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Memory embeddings |
| `OLLAMA_NUM_CTX` | `2048` | Context size |
| `OLLAMA_NUM_THREAD` | `8` | Ollama CPU threads |
| `OLLAMA_KEEP_ALIVE` | `10m` | Model keep-alive |
| `DB_PATH` | `data/myai.db` | SQLite database |
| `MAX_WEB_CHARS` | `30000` | Max extracted web text |
| `EXEC_TIMEOUT` | `10` | Python execution timeout |
| `EXECUTOR_MODE` | `container` | `container` or `subprocess` |
| `EXECUTOR_IMAGE` | `python:3.11-slim` | Executor image |
| `EXEC_MEMORY` | `256m` | Executor RAM |
| `EXEC_CPUS` | `1.0` | Executor CPU |
| `EXEC_PIDS` | `64` | Executor PID limit |
| `EXEC_OUTPUT_CHARS` | `12000` | Executor output limit |
| `SCHEDULER_INTERVAL_SECONDS` | `3600` | Scheduler interval |
| `SCHEDULER_MAX_CPU_PERCENT` | `70` | Learning CPU ceiling |
| `SCHEDULER_MAX_RAM_PERCENT` | `80` | Learning RAM ceiling |
| `SCHEDULER_AUTO_RESUME` | `false` | Auto-resume behavior |
| `LEARNING_MAX_RETRIES` | `5` | Legacy/configurable retry setting; long-running resilience uses retry-until-stop behavior |
| `MYAI_BACKUP_ROOT` | `data/backups` | Backup safe root |
| `MYAI_SQLITE_ROOT` | `data/sqlite` | External SQLite safe root |
| `WHISPER_CPP_BIN` | empty | Explicit whisper-cli path |
| `HOST` | `127.0.0.1` | API bind host |
| `PORT` | `8000` | API port |
| `GITHUB_TOKEN` | — | GitHub token |
| `GITHUB_API_URL` | — | GitHub Enterprise API base |
| `MYAI_PROJECT_ROOT` | configured | Project tool workspace |
| `MYAI_SQLSERVER_CONNECTION_STRING` | — | SQL Server connection |

## 41. Workspaceها

```text
projects/
self-repair/
```

`projects/` برای پروژه‌های تولیدشده و `self-repair/` برای snapshot، lesson و artifactهای self-repair/watchdog استفاده می‌شوند.

Runtime artifacts این workspaceها برای جلوگیری از آلودگی history در Git نادیده گرفته می‌شوند.

## 42. Docker

```bash
docker compose up --build
```

## 43. نصب

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
ollama pull qwen2.5:7b
python -m my_ai
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
ollama pull qwen2.5:7b
python -m my_ai
```

سپس:

```text
http://127.0.0.1:8000
```

نیازمندی پایه:

- Python 3.11+
- Ollama
- Internet برای مدل و منابع وب
- حداقل 16 GB RAM؛ 32 GB پیشنهاد می‌شود.
- GPU الزامی نیست.

## 44. تست

```bash
pip install -e .
pytest -q
python -m compileall -q my_ai tests
```

CI روی push و pull request اجرا می‌شود و تست‌ها، compile، security checks، dependency checks و Docker build را پوشش می‌دهد.

## 45. وضعیت و مرزهای فعلی

برای جلوگیری از ادعای بیش از implementation واقعی:

- File access جدید برای read/list/inspect/read read-only است؛ write در upload/generation صریح انجام می‌شود.
- prerequisite auto-install فعلاً برای dependencyهای Python شناخته‌شده است؛ نصب خودکار نرم‌افزارهای سیستم‌عاملی مانند FFmpeg/LibreOffice عمومی نیست.
- audio/video در implementation فعلی عمدتاً metadata را از `ffprobe` می‌گیرند؛ semantic transcription کامل نیازمند integration مربوطه است.
- file generation endpointها وجود دارند؛ تبدیل دستور طبیعی Chat به workflow کامل تولید هر نوع سند ممکن است به توسعه routing/agent بیشتری نیاز داشته باشد.
- extended feature routes در مسیر اجرای `python -m my_ai` ثبت می‌شوند.
- قابلیت‌های قدیمی project/self-update/code-generation ممکن است policy نوشتن مخصوص خود را داشته باشند؛ policy سراسری «کل سیستم read-only تا فرمان صریح» هنوز یک refactor واحد و سراسری نیست.

این بخش عمداً در README باقی مانده تا تفاوت بین «ماژول موجود»، «قابلیت پیاده‌سازی‌شده» و «قابلیت کامل end-to-end» مشخص باشد.

---

# English — Complete Feature & Module Inventory

## 1. Chat, Agent and Command Routing

- Local Ollama chat.
- Command Router.
- Agent orchestration.
- Context-aware responses.
- Persistent knowledge retrieval.
- Natural-language commands for learning, code, projects, security, Help, GitHub and files.
- Persian RTL and English LTR web UI.
- Chat file attachment and analysis integration.

## 2. LLM / Ollama

Supported configuration includes:

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `ROUTER_MODEL`
- `CODING_MODEL`
- `FALLBACK_MODEL`
- `EMBEDDING_MODEL`
- `OLLAMA_NUM_CTX`
- `OLLAMA_NUM_THREAD`
- `OLLAMA_KEEP_ALIVE`

CPU-only execution is supported and is the default. GPU layers are optional and default to zero.

## 3. Persistent Memory

Modules: `db.py`, `memory.py`, `metrics.py`

SQLite stores conversations, knowledge, learning sessions, experiments, project tasks, generated projects, security scans, Help updates, authentication sessions, permissions, settings and audit data.

Knowledge retrieval uses FTS5.

```text
GET /memory/knowledge
GET /memory/search?q=python&limit=8
```

## 4. Learning Engine

Modules: `learner.py`, `dynamic_learning.py`, `curriculum.py`, `advanced_curriculum.py`, `forex_curriculum.py`, `learning_resilience.py`, `scheduler.py`

Pipeline:

```text
Curriculum → topic selection → source retrieval → local-model extraction
→ SQLite persistence → lesson/examples/exercises/checklist
→ assessment → progress → next topic
```

Features include persistent learning, reference-source retrieval, lessons, exercises, assessment, progress tracking, independent concurrent learning paths, background execution, stop/resume controls, resource-aware scheduling and retry with backoff.

Supported learning paths:

- Rust
- Python
- C
- PHP
- JavaScript
- SQL Server / T-SQL
- MySQL
- SQLite
- Android / Kotlin
- iOS / Swift
- Pentest / Security Testing
- Cisco networking / IOS
- Forex

### Rust

The Rust path covers fundamentals through ownership, borrowing, lifetimes, async, unsafe, FFI, performance, security, production and capstone work.

### Forex

The Forex curriculum contains **121 explicit topics**, including professional capital/risk-management material and a Forex/MetaTrader capstone.


### Pentest

Pentest is an independent learning path covering security fundamentals, Linux/networking, web/API security, reconnaissance, asset discovery, vulnerability assessment, code review, security tooling, reporting and authorized project testing.

## 5. Learning Controls

The UI/API supports:

- active-learning listing
- stop learning
- resume learning
- progress/phase/topic visibility
- independent learning paths
- scheduler control

```text
GET  /learning
GET  /learning/active
GET  /learning/catalog
GET  /learning/status
POST /learning/{language}/stop
POST /learning/{language}/resume
POST /learning/start
POST /learning/step
POST /learning/learn
POST /learning/practice
```

## 6. Custom Courses

`settings_feature.py` supports custom courses with:

- course name and description
- custom topics
- topic goals
- source URLs
- progress tracking
- start/resume
- pause
- default Cisco course

```text
GET  /settings/courses
POST /settings/courses
GET  /settings/courses/{course_id}/progress
POST /settings/courses/{course_id}/start
POST /settings/courses/{course_id}/pause
POST /learning/{course_id}/start
```

## 7. Scheduler

`scheduler.py` provides background learning workers, independent paths, runtime status, start/stop controls, resource-aware waiting, graceful stop events and retry/backoff behavior.

```text
POST /scheduler/start
GET  /scheduler/status
POST /scheduler/stop
```

## 8. Resource Control

Modules: `resource_guard.py`, `settings_store.py`

Persistent settings:

| Setting | Default |
|---|---:|
| CPU max | 70% |
| CPU threads | 8 |
| RAM max | 80% |
| GPU layers | 0 |

The learning scheduler reads CPU/RAM settings live and waits when configured limits are exceeded.

## 9. Settings

Modules: `settings_feature.py`, `settings_store.py`, `settings_script.js`

Settings cover:

- GitHub API URL, repository, username and token verification.
- GitHub Enterprise.
- Self-update enable/approval/health URL.
- Self-repair enable/approval.
- Fast learning.
- Learning interval.
- Learning retry configuration.
- CPU/RAM/thread/GPU limits.
- User management.
- Per-user tool permissions.
- Custom courses.

Permission actions:

```text
read
write
execute
```

Managed tools include chat, code-generation, code-execution, learning, scheduler, github, security, database, voice, models, memory, web, projects, eval, self-update, self-repair, help and tools.

## 10. Authentication / Authorization

`auth.py` provides:

- account creation
- first-user admin bootstrap
- scrypt password hashing
- random salts
- 24-hour sessions
- session revocation
- admin/user roles
- per-tool permissions
- audit logging

Sensitive settings require administrator access.

## 11. Code Generation

Modules: `agent.py`, `llm.py`, `tooling.py`, `project_workspace.py`

Capabilities:

- goal decomposition
- tasks
- acceptance criteria
- memory retrieval
- code generation
- code fixing
- project generation
- project-state persistence

## 12. Project Planning / Workspaces

- project plans
- task tracking
- acceptance criteria
- isolated generated-project workspaces
- `projects/` runtime workspace
- tool execution restricted to the configured project workspace

```text
POST /projects/plan
GET  /projects/tasks
POST /tools/project
```

## 13. Toolchain

`tooling.py` provides toolchain/build/lint/test support for:

- Python
- C
- PHP
- JavaScript
- Rust
- Kotlin
- Swift
- Android
- iOS

The toolchain is not an unrestricted shell interface.

```text
GET  /tools/catalog
GET  /tools/doctor
POST /tools/project
```

## 14. Python Executor / Sandbox

Modules: `executor.py`, `executor_service.py`

Default mode is an isolated container with:

- no network
- read-only host filesystem view
- dropped capabilities
- `no-new-privileges`
- RAM/CPU/PID limits
- timeout
- output limits
- automatic container removal

Optional less-isolated mode:

```text
EXECUTOR_MODE=subprocess
```

## 15. SQL Tools

SQL Server:

- read-only schema inspection
- read-only queries
- Microsoft `mssql-python` support
- `MYAI_SQLSERVER_CONNECTION_STRING`

SQLite:

- read-only schema
- read-only queries
- controlled root via `MYAI_SQLITE_ROOT`

```text
GET  /tools/sqlserver/schema
POST /tools/sqlserver/query
GET  /tools/sqlite/schema
POST /tools/sqlite/query
```

## 16. Static Security Analysis

`security.py` checks for:

- secrets
- eval/exec
- shell execution
- weak hashes
- SQL injection patterns
- debug mode
- unsafe CORS
- DOM sinks
- path traversal
- plaintext passwords
- dependency manifests

```text
POST /security/scan
GET  /security/history
```

## 17. DAST

`dast.py` supports authorized local HTTP testing, route discovery, real requests, security headers, 500/debug leakage, reflection, TRACE, cookie flags, CSRF indicators, limited same-origin crawling and OpenAPI checks.

External targets require an explicitly supplied URL and appropriate authorization. External scanning is non-destructive and does not modify remote code.

## 18. Security/Test Policy

Explicit user instructions determine whether a security operation is:

- report-only
- test-only
- test + fix + retest
- inspection without file modification

## 19. Web Learning / Network Controls

Modules: `web_learner.py`, `network.py`

- URL ingestion
- content extraction
- web-text limit
- source/reference retrieval
- URL validation
- redirect validation
- DNS/IP validation
- public/private address controls
- DNS pinning for sensitive external requests

```text
POST /learn/url
```

## 20. Help / Documentation

`help.py` provides integrated Help, documentation lookup, practical guidance, current-doc comparison and proposed documentation updates.

Updates require explicit user approval.

```text
GET  /help
POST /help/ask
GET  /help/updates
POST /help/approve/{update_id}
POST /help/reject/{update_id}
```

## 21. Git / GitHub

`git_connector.py` supports reading repositories, trees, files, issues, pull requests and branches.

Controlled writes can create branches and create/update files and require `allow_write=true` plus appropriate token permissions.

```text
GET  /git/repo
GET  /git/tree
GET  /git/file
GET  /git/issues
GET  /git/pulls
GET  /git/branches
POST /git/branch
PUT  /git/file
GET  /git/check
POST /git/login
POST /git/logout
```

## 22. Local Files / Chat Attachments

Modules: `local_files.py`, `file_processing.py`, `multimodal.py`, `feature_routes.py`

Current capabilities:

- filesystem roots
- directory listing
- inspection
- read-only file reading
- upload into the application workspace
- file analysis
- Chat file attachment
- MIME/type detection
- text extraction
- DOCX/XLSX/PDF extraction
- image metadata
- Ollama vision analysis where supported
- audio/video metadata through `ffprobe` where installed
- prerequisite detection

Upload limit: **100 MiB**.

```text
GET  /files/roots
GET  /files/list
POST /files/inspect
POST /files/read
POST /files/upload
POST /files/analyze
POST /files/prerequisites
```

## 23. Prerequisite Installation

Known Python prerequisites can be installed automatically with pip when missing:

- `python-docx`
- `openpyxl`
- `python-pptx`
- `PyMuPDF`
- `Pillow`

System prerequisite installation uses explicit, platform-specific package-manager commands and requires explicit administrator confirmation for system changes. It is not an unrestricted arbitrary shell installer.

## 24. Document Generation

Supported generated formats:

- DOCX
- XLSX
- PDF
- PPTX

```text
POST /files/generate/docx
POST /files/generate/xlsx
POST /files/generate/pdf
POST /files/generate/pptx
```

## 25. Multimodal Processing

`multimodal.py` supports text, images, DOCX, XLSX, PDF, audio/video metadata and safe inspection of unknown/binary types.

Vision analysis can use an Ollama vision-capable model. Full audio/video semantic transcription is dependent on the configured voice/transcription integration.

## 26. Voice

`voice.py` uses browser `SpeechRecognition`/`webkitSpeechRecognition` and `speechSynthesis`.

Supported language codes:

```text
fa-IR
en-US
```

Microphone permission and browser support are required for speech recognition.

## 27. Backup / Restore

Modules: `backup_crypto.py`, `config.py`, `db.py`

- controlled backup/restore roots
- runtime data backup/restore
- backup-related cryptographic support
- safe-root configuration via `MYAI_BACKUP_ROOT`

## 28. Self-update

`self_update.py` uses isolated worktrees, testing, snapshots, activation, health checks and watchdog/rollback behavior.

Self-update health URLs are restricted to the local host.

## 29. Self-repair

`self_repair.py` performs diagnosis, lesson-aware patch generation, isolated `compileall + pytest`, explicit approval, application and rollback on failure.

Artifacts include:

- `self-repair/`
- `self-repair/lessons.jsonl`
- `fix_attempts` database records

## 30. Watchdog

`watchdog.py` supports health monitoring around update/activation and helps trigger rollback behavior when a deployment fails.

## 31. Platform Abstraction

`platform.py` detects operating-system/platform characteristics and provides abstractions used by cross-platform workflows and toolchains.

## 32. Capabilities / Skill / Domain Registry

Modules:

- `capabilities.py`
- `skill_engine.py`
- `domain_registry.py`

These provide capability registration, domain/skill organization and integration with routing/agent workflows.

## 33. Command Policy

`command_policy.py` applies command/tool execution policy and distinguishes read/write/execute operations for sensitive workflows.

## 34. Metrics / Observability

`metrics.py` provides runtime metrics used by diagnostics and operational visibility.

## 35. Notifications

`notifications.py` provides the runtime notification/event abstraction used by application workflows.

## 36. Audit / Decision Log

`auth.py` records audit events including user, tool, action, status and details. `decision_log.py` stores decision-log information used by internal workflows.

## 37. Web UI

Modules: `ui.py`, `ui_extensions.py`

The UI includes:

- Chat
- Learning dashboard
- learning progress
- stop/resume controls
- Settings
- Help
- Voice
- file attachment
- file analysis
- bilingual RTL/LTR presentation

## 38. FastAPI / OpenAPI

```text
/docs
/redoc
```

The API inventory is documented above and includes Chat, Code, Security, Learning, Scheduler, Memory, Help, Git, Tools, Settings and File Processing routes.

## 39. Configuration

See the Persian configuration table above for the full environment-variable inventory. Important values include Ollama model settings, database path, executor limits, scheduler limits, backup/SQLite roots, GitHub settings, SQL Server connection and project workspace.

## 40. Docker

```bash
docker compose up --build
```

## 41. Installation

Requirements:

- Python 3.11+
- Ollama
- Internet only for explicitly online capabilities (LLM provider, confirmed web learning, learning sources, Git/GitHub and prerequisite installation)
- at least 16 GB RAM; 32 GB recommended as a baseline; runtime settings are adapted to detected hardware
- GPU not required

Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
ollama pull qwen2.5:7b
python -m my_ai
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
ollama pull qwen2.5:7b
python -m my_ai
```

## 42. Testing / CI

```bash
pip install -e .
pytest -q
python -m compileall -q my_ai tests
```

CI runs on push and pull requests and includes automated testing, compile checks, security/dependency checks and Docker build coverage.

## 43. Current Implementation Boundaries

The following are documented explicitly so the inventory does not overstate implementation:

- New local-file read/list/inspect/read routes are read-only; writes happen only through explicit upload/generation operations in that feature layer.
- Automatic prerequisite installation currently targets known Python dependencies rather than arbitrary operating-system packages such as FFmpeg or LibreOffice.
- Audio/video processing includes local transcription when whisper.cpp is configured, local semantic transcript analysis, and video frame/combined semantic analysis when a local Ollama model is available. Missing local engines are reported instead of falling back to cloud services.
- Chat-to-document generation is integrated for DOCX, XLSX, PDF and PPTX through /files/generate/from-chat, with explicit format selection and workspace-safe output.
- Startup prerequisite checks are centralized in my_ai.api, so both python -m my_ai and direct uvicorn my_ai.api:app use the same registration/startup path.
- Application-wide mutation policy is enforced centrally by the API policy engine and database mutation boundary. MYAI_READ_ONLY=true blocks API mutations and runtime SQLite writes; Docker deployments can additionally use a read-only root filesystem. Writes performed by unrelated external processes outside the My-AI process are intentionally outside application control.

This section is intentional: it distinguishes **module exists**, **feature implemented**, and **fully end-to-end integrated** so the next development pass can target missing pieces precisely.

---

# Module Inventory / فهرست فایل‌های ماژول

| Module | Responsibility |
|---|---|
| `__main__.py` | Application startup and runtime feature registration |
| `api.py` | Main FastAPI application and API routes |
| `agent.py` | Agent orchestration and request workflows |
| `router.py` | Compatibility facade for layered command routing |
| `llm.py` | Ollama/LLM abstraction |
| `db.py` | SQLite database layer + mutation guard |
| `memory.py` | Persistent memory helpers |
| `metrics.py` | Runtime metrics |\n| `observability.py` | Structured JSON logging and correlation fields |\n| `core/` | Stable core protocols/contracts |\n| `domain/` | Layered domain services including canonical router |
| `learner.py` | Learning engine |
| `dynamic_learning.py` | Dynamic topic/language resolution and learning behavior |
| `learning_resilience.py` | Retry-until-stop resilience patch |
| `scheduler.py` | Background learning scheduler/workers |
| `resource_guard.py` | CPU/RAM resource gating |
| `curriculum.py` | Main curricula and aliases |
| `advanced_curriculum.py` | Advanced curriculum selection/registration |
| `forex_curriculum.py` | 121-topic Forex curriculum |
| `security.py` | Static security analysis |
| `dast.py` | Dynamic application security testing |
| `network.py` | Network/URL/DNS security controls |
| `tooling.py` | Toolchain/project/database tools |
| `executor.py` | Python execution abstraction |
| `executor_service.py` | Python executor service implementation |
| `project_workspace.py` | Generated project workspace management |
| `git_connector.py` | GitHub integration |
| `help.py` | Integrated Help/documentation system |
| `web_learner.py` | Web learning and source retrieval |
| `local_files.py` | Local filesystem access helpers |
| `file_processing.py` | File extraction/generation/prerequisites |
| `multimodal.py` | Multimodal file inspection/analysis |
| `voice.py` | Voice-related backend support |
| `settings_feature.py` | Settings, users, courses and permissions |
| `settings_store.py` | Persistent settings storage |
| `settings_script.js` | Settings UI client logic |
| `auth.py` | Authentication, authorization and audit |
| `command_policy.py` | Command/tool safety policy |
| `capabilities.py` | Capability registry |
| `skill_engine.py` | Skill execution/organization |
| `domain_registry.py` | Domain registry |
| `platform.py` | OS/platform abstraction |
| `notifications.py` | Notification/event abstraction |
| `backup_crypto.py` | Backup cryptographic support |
| `self_update.py` | Self-update workflow |
| `self_repair.py` | Self-repair workflow |
| `watchdog.py` | Health/watchdog and rollback support |
| `self_diagnostics.py` | Continuous self-diagnostics and hardware-aware reporting |
| `decision_log.py` | Decision logging |
| `ui.py` | Main web UI |
| `ui_extensions.py` | Runtime UI extensions for files and learning controls |

---

# Quick Checklist / چک‌لیست برای پیدا کردن قسمت‌های فراموش‌شده

- [x] Local Ollama Chat
- [x] Agent / Command Router
- [x] Persistent SQLite + FTS5 Memory
- [x] Learning Engine
- [x] Multiple concurrent learning paths
- [x] Learning stop/resume controls
- [x] Learning Scheduler
- [x] Resource control
- [x] Rust curriculum
- [x] Python/C/PHP/JavaScript curricula
- [x] SQL Server/MySQL/SQLite curricula
- [x] Android/Kotlin and iOS/Swift curricula
- [x] Pentest curriculum
- [x] Cisco curriculum
- [x] Forex 121-topic curriculum
- [x] Custom courses
- [x] Code generation
- [x] Project planning
- [x] Toolchain detection/build/lint/test
- [x] Python container executor
- [x] SQL Server read-only tools
- [x] SQLite read-only tools
- [x] Static security analysis
- [x] DAST
- [x] External-target safety controls
- [x] Web Learning
- [x] Help system
- [x] Documentation update approval workflow
- [x] Git/GitHub read operations
- [x] Controlled GitHub write operations
- [x] Authentication / roles
- [x] Per-tool permissions
- [x] Audit logging
- [x] Settings UI
- [x] CPU/RAM/GPU settings
- [x] Local file listing/reading/inspection
- [x] Chat file attachment
- [x] DOCX/XLSX/PDF extraction
- [x] Image metadata/vision analysis path
- [x] Fully offline image generation module (chat-integrated manga/comic generation through local Automatic1111)
- [x] Audio/video metadata path
- [x] Prerequisite detection/install for known Python packages
- [x] DOCX/XLSX/PDF/PPTX generation
- [x] Voice input/output path
- [x] Backup/restore support
- [x] Self-update
- [x] Self-repair
- [x] Watchdog/rollback support
- [x] Platform abstraction
- [x] Capability/skill/domain registries
- [x] Metrics
- [x] Notifications abstraction
- [x] Docker
- [x] OpenAPI docs
- [x] Bilingual UI/README


## Local Ownership and Self-Development Policy

My-AI follows a **local-first, self-owned architecture**.

The default engineering rule for every new capability is:

**MY-AI native/local implementation → local open-source backend → optional external provider**

An external company API must not become a mandatory dependency merely for convenience. LLM backends and Git/GitHub are explicit exceptions because they currently provide infrastructure that may be external by design. Web access is used only for capabilities that inherently require current internet content or an explicitly requested online operation.

### Hardware-aware operation

The application must adapt to the machine on which it is running instead of assuming one permanent hardware profile.

At startup and during diagnostics it records available CPU, RAM, operating system, Python version and other detectable accelerator information. Resource settings, learning concurrency, model context/thread settings and background workloads should be selected from the detected capacity and the user's persistent limits.

The repository's documented minimum/recommended hardware is a baseline only; actual runtime decisions must use live hardware detection.

### Continuous self-check

After startup, and periodically while running, My-AI checks itself:

- Python compilation with compileall.
- Full pytest suite.
- Git working-tree and current commit state.
- Runtime hardware information.
- Diagnostic history and recurring failures.

Reports are stored locally under data/diagnostics/ and in SQLite and are exposed through:

```text
GET /self-diagnostics/report
GET /self-diagnostics/history
```

### Initial/Beta self-development policy

During the initial and beta releases the system is **report-only**.

If it finds a bug, regression, failed test, performance problem or hardware-specific optimization opportunity, it creates a diagnostic report. It does not automatically modify source code, install arbitrary packages, change permissions, publish changes or alter its own policy.

The intended later lifecycle is:

```text
detect
  ↓
diagnose
  ↓
propose
  ↓
isolated test
  ↓
report
  ↓
policy/approval
  ↓
apply
  ↓
test
  ↓
rollback on failure
```

The existing self-repair subsystem is the foundation for this later phase.

### Self-created modules

After the self-development phase is enabled, the intended user workflow is:

```text
User: "برای خودت یک ماژول X بساز"
                 ↓
My-AI inspects its own architecture
                 ↓
designs the module
                 ↓
creates code + tests in isolation
                 ↓
runs compile/test/security checks
                 ↓
produces a change report
                 ↓
applies according to the active policy
                 ↓
registers the capability
                 ↓
updates documentation
```

This makes future module expansion a capability of My-AI itself rather than requiring every module to be manually created externally.

No claim is made that the system is already a fully autonomous software engineer. The initial and beta phases deliberately collect evidence and reports first so the later self-modification phase can be introduced on top of tested rollback, audit and validation mechanisms.

### Self-development documentation

See `docs/help/self-development.md` for the lifecycle, hardware adaptation rules, ownership policy and future self-module workflow.

## Network and Offline Policy

My-AI follows a strict **local-first / offline-by-default** rule.

### Allowed online operations

1. **LLM backend**, when the configured backend itself is online.
2. **Chat knowledge acquisition**: when local knowledge is insufficient, the chat says it does not know and searches the web only after explicit user confirmation. The evidence is then learned and added to the matching curriculum topic, or a new topic is created.
3. **Learning resources**: explicitly configured educational sources and scheduled learning review/update workflows.
4. **Pentest/security tooling**: explicitly requested tools, targets, and resources that require network access.
5. **Educational tool/prerequisite installation**: missing dependencies may be installed online by the prerequisite manager.
6. **Git/GitHub**: repository, issue, pull-request and controlled Git operations are online by design.

### Everything else

All other application features are intended to operate locally without internet access: local memory/database, file processing, generated documents, local image generation, scheduler state, audit logs, settings, local voice processing, local code/project operations, and local security analysis.

The image generator is offline-only and accepts only a local Automatic1111 endpoint. Automatic1111 exposes its API when launched with `--api`.

### Unknown-answer learning flow

The chat must not guess. If local knowledge is insufficient it reports that it does not know and asks for confirmation. After confirmation, the web-learning pipeline searches permitted public sources, fetches allowed pages, extracts the lesson, records sources, stores knowledge, and extends the curriculum when necessary.

### Startup prerequisite policy

On every application startup, My-AI checks Python dependencies declared in `pyproject.toml` and selected system prerequisites. Missing Python packages are installed automatically only when `MYAI_AUTO_INSTALL_PREREQUISITES=true` is explicitly enabled. The default is `false`, so application startup is non-mutating and does not repeatedly invoke package managers; unresolved prerequisites are reported.

This policy is part of the development contract: new features must remain offline by default unless they belong to an explicitly allowed online category above. New network-capable features must document their reason, permission boundary, and user-facing behavior.

## Implementation verification / وضعیت تکمیل

این موارد در نسخه فعلی دیگر به‌عنوان backlog کدنویسی ثبت نمی‌شوند:

- Unified API policy + deny-by-default route handling + application/database read-only enforcement.
- Structured semantic router with schema validation and regression coverage؛ deterministic matching فقط safety fallback است وقتی classifier در دسترس نیست.
- Hybrid FTS5 + local embedding retrieval با provenance، verification state و confidence calibration بر اساس retrieval judgments.
- Knowledge management UI در /admin/knowledge با verify/audit workflow.
- Skill evidence، sandbox benchmark، score مستقل و version-aware revalidation.
- Streaming/multi-session، backup/export/import با versioning و SHA-256 integrity metadata.
- Model health با availability per role و fallback readiness.
- Local whisper.cpp/Piper health checks و semantic audio/video analysis.
- System prerequisite installation با package-managerهای پشتیبانی‌شده و تأیید صریح admin.
- Chat-to-document برای DOCX/XLSX/PDF/PPTX و مسیر browser E2E.
- Structured JSON observability و correlation ID در HTTP requests.
- Direct uvicorn my_ai.api:app و python -m my_ai از startup gate یکسان استفاده می‌کنند.

دو محدودیت ذاتی همچنان صریح هستند: «OS-wide» به معنی کنترل writeهای فرآیندهای خارجی سیستم‌عامل نیست، و uv.lock در محیط بدون دسترسی شبکه تولید نشده است؛ dependency source of truth خود pyproject.toml است و requirements.lock یک compatibility snapshot است.

## Engineering governance

- Architecture: `docs/ARCHITECTURE.md`
- Product scope and feature-creep guardrails: `PROJECT_SCOPE.md`
- Contribution rules: `CONTRIBUTING.md`
- Security policy: `SECURITY.md`
- Dependency source of truth: `pyproject.toml`; `requirements.txt` is a compatibility entry point only.
- Central API/tool authorization and global read-only enforcement: `my_ai/access_policy.py`.
