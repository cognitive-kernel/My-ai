# My-AI — Local Personal AI Assistant

My-AI یک دستیار هوش مصنوعی **local-first** است که روی Ollama اجرا می‌شود و برای استفاده شخصی، یادگیری مستمر، حافظه پایدار، تولید کد، برنامه‌ریزی پروژه و بررسی امنیتی طراحی شده است.

هدف پروژه این است که مدل محلی فقط یک چت‌بات نباشد؛ بلکه با ذخیره دانش و روند یادگیری در SQLite بتواند در طول زمان برای پروژه‌های شما دانش قابل بازیابی جمع کند.

## امکانات اصلی

### دستیار و چت
- اجرای مدل محلی از طریق Ollama؛ بدون نیاز به API پولی.
- حافظه پایدار گفتگو و دانش با SQLite + FTS5.
- پاسخ‌های context-aware بر اساس گفتگو و دانش ذخیره‌شده.
- تشخیص دستورهای یادگیری، ساخت برنامه، پروژه، امنیت و راهنما.
- رابط وب فارسی RTL و انگلیسی LTR.
- ورودی صوتی مرورگر و خروجی گفتاری.

### یادگیری خودکار و ماندگار
در چت می‌توانید بگویید:

```text
پایتون یاد بگیر
PHP یاد بگیر
C یاد بگیر
JavaScript یاد بگیر
SQL Server یاد بگیر
MySQL یاد بگیر
SQLite یاد بگیر
Android یاد بگیر
iOS یاد بگیر
پن‌تست یاد بگیر
```

فرآیند یادگیری:
1. انتخاب موضوع بعدی از curriculum.
2. دریافت مستندات و منابع مرجع.
3. استخراج دانش با مدل محلی.
4. ذخیره منبع و یادداشت پایدار در SQLite.
5. ساخت درس، مثال، تمرین و checklist.
6. ارزیابی درس.
7. ثبت پیشرفت.
8. ادامه مرحله بعدی توسط Scheduler.

درصد پیشرفت بر اساس موضوع‌های تکمیل‌شده محاسبه می‌شود و نمره ارزیابی جداگانه نگه‌داری می‌شود؛ بنابراین تکمیل curriculum به‌معنی ادعای «تسلط ۱۰۰٪» نیست.

### مسیرهای یادگیری فعلی
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

مسیر Pentest مستقل از زبان PHP است و مباحثی مانند مبانی امنیت، Linux و شبکه، امنیت وب، شناسایی دارایی، ارزیابی آسیب‌پذیری، تست Web/API، code review، ابزارهای امنیتی، گزارش‌دهی و آزمایش امنیتی پروژه PHP را پوشش می‌دهد.

## پوشه‌های کاری پروژه و Self-Repair

در ریشه repository دو workspace اختصاصی وجود دارد:

- `projects/`: هر بار که My-AI یک پروژه تولید می‌کند، یک پوشه مستقل با نام امن‌شده پروژه می‌سازد و فایل‌های همان پروژه را داخل همان پوشه قرار می‌دهد.
- `self-repair/`: snapshot، lesson و artifactهای مربوط به self-repair و watchdog در این workspace نگه‌داری می‌شوند.

محتویات تولیدشده این دو workspace runtime هستند و برای جلوگیری از آلوده‌شدن history Git در `.gitignore` نادیده گرفته می‌شوند.

## تولید کد و پروژه

نمونه دستور:

```text
برای من یک API مدیریت کاربران با پایتون بساز
یک پروژه PHP برای مدیریت کاربران بنویس
یک برنامه JavaScript بنویس
```

موتور پروژه می‌تواند:
- هدف را به task و acceptance criteria تبدیل کند.
- دانش مرتبط را از حافظه بازیابی کند.
- کد تولید کند.
- برای Python یک اعتبارسنجی/اجرای محدود انجام دهد.
- پروژه تولیدشده را در حافظه پروژه ثبت کند.

### اجرای کد Python

اجرای Python به‌صورت پیش‌فرض با **Container Executor** انجام می‌شود. کانتینر اجرای کد شبکه ندارد (`--network none`)، filesystem اصلی را فقط خواندنی می‌بیند، capabilityها حذف می‌شوند، `no-new-privileges` فعال است، RAM/CPU/PID محدود است و timeout و محدودیت خروجی دارد. کانتینر پس از اجرا حذف می‌شود.

حالت subprocess فقط با `EXECUTOR_MODE=subprocess` فعال می‌شود و برای کد کاملاً غیرقابل‌اعتماد توصیه نمی‌شود. برای ایزولیشن بالاتر، VM جداگانه گزینه مناسب‌تری است.

## امنیت، Static Analysis و DAST

امنیت دو لایه اصلی دارد:

1. **Static/source analysis**
   - secrets
   - eval/exec
   - shell execution
   - hashهای ضعیف
   - الگوهای SQL injection
   - debug mode
   - CORS ناامن
   - DOM sinks
   - path traversal
   - plaintext passwords
   - dependency manifest
2. **DAST**
   - اجرای پروژه‌های محلی پشتیبانی‌شده روی loopback.
   - کشف routeهای متداول.
   - ارسال درخواست HTTP واقعی.
   - بررسی security headers، خطاهای 500، debug/stack-trace leakage، reflection، TRACE، cookie flags و نشانه‌های CSRF.
   - crawl محدود same-origin و بررسی endpointهای OpenAPI در تست‌های مجاز.

### سیاست اجرای تست

رفتار پیش‌فرض با دستور صریح کاربر کنترل می‌شود:

```text
از پروژه تست بگیر
→ گزارش امنیتی، بدون اصلاح

پن‌تست بگیر و فقط گزارش بده
→ فقط گزارش، بدون اصلاح

پن‌تست بگیر و باگ‌ها را رفع کن
→ بررسی، اصلاح و بررسی مجدد

پروژه را بررسی کن و فقط اشکالات را بگو
→ گزارش بدون تغییر فایل‌ها
```

دستور صریح کاربر بر پیش‌فرض غلبه دارد.

### هدف خارجی

برای سایت یا سرویس خارجی، آدرس باید **صریحاً توسط کاربر ارائه شود**:

```text
پن‌تست آدرس: https://example.com
پن‌تست آدرس: https://example.com فقط گزارش بده
```

اسکن خارجی non-destructive است و برای اصلاح remote استفاده نمی‌شود. هدف باید متعلق به شما باشد یا مجوز صریح تست آن را داشته باشید.

## Git و GitHub

My-AI یک connector برای GitHub دارد.

### خواندن
- repository
- tree
- file
- issues
- pull requests
- branches

### نوشتن
- ساخت branch
- ایجاد/به‌روزرسانی فایل

نوشتن فقط با `allow_write=true` فعال می‌شود.

### اتصال

```bash
export GITHUB_TOKEN="YOUR_TOKEN"
```

برای GitHub Enterprise:

```bash
export GITHUB_API_URL="https://github.example/api/v3"
```

تست‌های نمونه:

```text
GET /git/repo?repository=owner/repo
GET /git/tree?repository=owner/repo&ref=main
GET /git/file?repository=owner/repo&path=README.md
GET /git/issues?repository=owner/repo
GET /git/pulls?repository=owner/repo
GET /git/branches?repository=owner/repo
```

برای عملیات نوشتن، `allow_write=true` و مجوزهای مناسب token لازم است.

## راهنمای هوشمند و به‌روزرسانی مستندات

My-AI یک **راهنمای یکپارچه داخل خود برنامه** دارد:

```text
GET /help
```

در رابط کاربری، بخش‌های مختلف دکمه «راهنما» دارند و کاربر می‌تواند همان بخش را در صفحه راهنما باز کند.

راهنمای هوشمند دو کار انجام می‌دهد:

### روش اول — توضیح قابلیت
می‌توانید از خود My-AI بپرسید:

```text
GitHub را چطور به My-AI وصل کنم؟
Docker را چطور اجرا کنم؟
پن‌تست این بخش چطور کار می‌کند؟
یادگیری Python را چطور شروع کنم؟
```

دستیار از راهنمای داخلی و مستندات مرتبط استفاده می‌کند و پاسخ عملی می‌دهد.

### روش دوم — بررسی تغییرات بیرونی
برای سرویس‌هایی که ممکن است روش اتصالشان تغییر کند، My-AI می‌تواند مستندات جدید را جست‌وجو کند، روش فعلی پروژه را با منابع جدید مقایسه کند و در صورت نیاز یک **پیشنهاد تغییر راهنما** بسازد.

منطق تأیید:

```text
سؤال کاربر
  ↓
راهنمای داخلی
  +
جست‌وجوی مستندات فعلی
  ↓
پاسخ عملی
  ↓
مقایسه روش فعلی با مستندات جدید
  ↓
پیشنهاد تغییر
  ↓
تأیید کاربر
  ↓
ثبت به‌روزرسانی در راهنمای برنامه
```

تغییرات پیشنهادی بدون تأیید کاربر اعمال نمی‌شوند.

منابع جست‌وجو برای بخش‌های شناخته‌شده تا حد امکان به مستندات رسمی محدود می‌شوند؛ برای مثال GitHub، Python، PHP، Docker، FastAPI و منابع امنیتی رسمی/مرجع.

## Web Learning

می‌توان یک URL مشخص را مستقیماً به سیستم یادگیری داد:

```text
POST /learn/url
{
  "url": "https://docs.python.org/3/",
  "topic": "Python"
}
```

برای جست‌وجوی منابع موردنیاز راهنمای هوشمند نیز از جست‌وجوی وب و سپس دریافت محتوای صفحات استفاده می‌شود.

## حافظه

اطلاعات اصلی در SQLite ذخیره می‌شوند:
- conversations
- knowledge
- learning sessions
- experiments
- project tasks
- generated projects
- security scans
- help updates

جست‌وجوی دانش با FTS5 انجام می‌شود.

نمونه:

```text
GET /memory/knowledge
GET /memory/search?q=python&limit=8
```

## Scheduler

Scheduler یادگیری را در پس‌زمینه ادامه می‌دهد.

```text
POST /learning/learn
{
  "language": "Python",
  "interval_seconds": 3600
}

GET /scheduler/status
POST /scheduler/stop
```

بازه فعلی interval از ۶۰ ثانیه تا ۲۴ ساعت است.

## تمرین و ارزیابی

برای تمرین:

```text
POST /learning/practice
{
  "message": "تفاوت list و tuple در Python چیست؟"
}
```

نتیجه تمرین و ارزیابی در روند یادگیری قابل استفاده است.

## Voice

رابط وب از قابلیت‌های مرورگر استفاده می‌کند:

- `SpeechRecognition` / `webkitSpeechRecognition`
- `speechSynthesis`
- زبان فارسی: `fa-IR`
- زبان انگلیسی: `en-US`

پشتیبانی Speech Recognition به مرورگر و permission میکروفون وابسته است.

## API

مستندات API:

```text
/docs
/redoc
```

Endpointهای مهم:

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
POST /learning/practice

POST /projects/plan
GET  /projects/tasks

GET /memory/search
GET /memory/knowledge

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
```

## Self-update و Self-repair

دو مسیر جدا وجود دارد:

- **Self-update**: وضعیت واقعی Git را می‌خواند؛ update در worktree جداگانه تست می‌شود؛ قبل از activation snapshot ساخته می‌شود و watchdog در صورت شکست rollback می‌کند.
- **Self-repair**: ابتدا diagnose محلی اجرا می‌شود، سپس مدل coding با lessons قبلی یک unified patch تولید می‌کند. patch در worktree ایزوله با `compileall + pytest` تست می‌شود و فقط پس از تأیید صریح کاربر روی working tree اعمال می‌شود. اگر تست پس از اعمال شکست بخورد، patch به commit پایه rollback می‌شود.
- `self-repair/lessons.jsonl` و جدول `fix_attempts` برای بستن حلقه یادگیری استفاده می‌شوند و lessons اخیر در promptهای تولید کد و patch قرار می‌گیرند.
- درخواست‌های HTTP به مقصدهای خارجی با DNS pinning انجام می‌شوند: IP عمومی در زمان request انتخاب و همان IP برای اتصال TCP استفاده می‌شود، در حالی که hostname برای Host/SNI حفظ می‌شود.

## Docker

اجرای پروژه:

```bash
docker compose up --build
```

## نصب

نیازمندی‌ها:
- Python 3.11+
- Ollama
- اتصال اینترنت برای دریافت مدل و مستندات
- حداقل 16 GB RAM؛ 32 GB پیشنهاد می‌شود.

### Windows

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
ollama pull qwen2.5:7b
python -m my_ai
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull qwen2.5-coder:7b
python -m my_ai
```

سپس:

```text
http://127.0.0.1:8000
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| OLLAMA_BASE_URL | http://127.0.0.1:11434 | آدرس Ollama |
| OLLAMA_MODEL | qwen2.5:7b | مدل پیش‌فرض |
| ROUTER_MODEL | qwen2.5:1.5b | مدل سبک برای وظایف routing/classification |
| CODING_MODEL | qwen2.5:7b | مدل تولید/اصلاح کد |
| FALLBACK_MODEL | qwen2.5:3b | مدل جایگزین هنگام شکست مدل اصلی |
| EMBEDDING_MODEL | nomic-embed-text | مدل embedding حافظه |
| OLLAMA_NUM_CTX | 4096 | context window |
| OLLAMA_NUM_THREAD | 6 | تعداد thread پیش‌فرض |
| OLLAMA_KEEP_ALIVE | 30m | مدت نگه‌داری مدل در Ollama |
| DB_PATH | data/myai.db | پایگاه‌داده پایدار |
| MAX_WEB_CHARS | 30000 | حداکثر متن استخراج‌شده از وب |
| EXEC_TIMEOUT | 10 | timeout اجرای Python |
| EXECUTOR_MODE | container | حالت اجرا: container یا subprocess |
| EXECUTOR_IMAGE | python:3.11-slim | image اجرای Python |
| EXEC_MEMORY | 256m | سقف RAM کانتینر |
| EXEC_CPUS | 1.0 | سقف CPU کانتینر |
| EXEC_PIDS | 64 | سقف process کانتینر |
| EXEC_OUTPUT_CHARS | 12000 | سقف خروجی |
| HOST | 127.0.0.1 | آدرس bind API |
| PORT | 8000 | پورت API |
| GITHUB_TOKEN | — | token اتصال GitHub |
| GITHUB_API_URL | — | API پایه GitHub Enterprise |

## معماری

```text
Web UI / Voice
      |
      v
   FastAPI
      |
      +--> Command Router / Agent
      |      +--> Chat
      |      +--> Learning
      |      +--> Code generation
      |      +--> Project planning
      |      +--> Security
      |      +--> Help / Documentation update
      |      +--> Git / GitHub
      |
      +--> Ollama local LLM
      +--> SQLite + FTS5 memory
      +--> Official/reference web sources
      +--> Container Python Executor
      +--> DAST runner
      +--> Learning scheduler
```

## مرز فنی مهم

این پروژه وزن‌های مدل پایه را retrain نمی‌کند.

مدل محلی موتور استدلال است و My-AI قابلیت‌های زیر را به آن اضافه می‌کند:
- حافظه خارجی پایدار
- دریافت منابع
- curriculum
- درس و تمرین
- ارزیابی
- اجرای محدود
- تولید پروژه
- security testing
- scheduler
- راهنمای هوشمند
- اتصال Git/GitHub

این طراحی برای سخت‌افزار معمولی مناسب‌تر از آموزش مجدد وزن‌های یک مدل بزرگ است.

## عیب‌یابی سریع

- **مدل پاسخ نمی‌دهد:** Ollama و نام مدل را بررسی کنید.
- **یادگیری وب کار نمی‌کند:** اتصال شبکه و URL منبع را بررسی کنید.
- **Git وصل نمی‌شود:** `GITHUB_TOKEN`، `owner/repo` و مجوز token را بررسی کنید.
- **GitHub Enterprise وصل نمی‌شود:** `GITHUB_API_URL` را بررسی کنید.
- **پن‌تست محلی اجرا نمی‌شود:** مسیر پروژه، framework، runtime و dependencyها را بررسی کنید.
- **URL خارجی رد می‌شود:** فقط URL صریح http/https با مقصد عمومی مجاز است.
- **اصلاح نمی‌خواهید:** از «فقط گزارش بده» یا «فقط تست بگیر» استفاده کنید.
- **روش یک سرویس خارجی تغییر کرده:** از بخش «راهنما» سؤال کنید تا مستندات فعلی جست‌وجو و با روش موجود مقایسه شود.

## تست و CI

بعد از دریافت repository:

```bash
pip install -e .
pytest -q
python -m compileall -q my_ai tests
```

موارد پایه برای بررسی دستی:
1. Ollama پاسخ می‌دهد.
2. صفحه `127.0.0.1:8000` باز می‌شود.
3. یادگیری Python شروع می‌شود.
4. مسیرهای SQL و موبایل قابل انتخاب هستند.
5. مسیر Pentest قابل انتخاب است.
6. dashboard بعد از تکمیل موضوع تغییر می‌کند.
7. درخواست تولید کد پاسخ می‌دهد.
8. صفحه `/help` باز می‌شود.
9. سؤال GitHub در Help پاسخ می‌گیرد.
10. تغییر پیشنهادی Help تا قبل از تأیید کاربر اعمال نمی‌شود.

CI تست‌های خودکار را روی push و pull request اجرا می‌کند.


## وضعیت فعلی پروژه

قابلیت‌های اصلی و سخت‌سازی‌های فنی در repository پیاده‌سازی شده‌اند. CI روی آخرین commit با موفقیت اجرا شده و تست‌های خودکار سبز هستند؛ اعلام «۱۰۰٪» همچنان فقط بعد از عبور تست نهایی محیط واقعی انجام می‌شود.

### تکمیل‌شده
- Container Executor ایزوله برای Python
- Web Learner با DNS/IP و redirect validation
- Help UI بدون تزریق HTML از خروجی مدل
- تأیید و رد به‌روزرسانی‌های راهنما
- API با mutable defaultهای اصلاح‌شده
- GitHub Actions برای compile و pytest
- Static Security Analysis و DAST خارجی؛ DAST محلی فقط در sandbox تأییدشده
- curriculum، حافظه پایدار و Scheduler
- Voice، Git/GitHub و رابط وب

### تست نهایی باقی‌مانده
- CI واقعی روی آخرین commit: موفق، ۱۸ تست سبز در workflow تست‌ها و compileall موفق
- تست end-to-end روی محیط دارای Ollama و Docker
- تست دستی نهایی UI، Voice، Learning، GitHub و Security
