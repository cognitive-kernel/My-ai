# My-AI — Local Personal AI Assistant

My-AI is a **local-first personal AI assistant** built around Ollama, FastAPI and SQLite. It provides natural-language chat, persistent memory, continuous learning, code and project generation, controlled code execution, Git/GitHub integration, documentation help, voice, local-file processing, resource control, self-update and self-repair.

این پروژه یک دستیار هوش مصنوعی **local-first** است که مدل را به‌صورت محلی اجرا می‌کند و برای گفتگو، یادگیری، درک context، تحقیق، برنامه‌ریزی و تولید پروژه‌های نرم‌افزاری طراحی شده است.

## قابلیت‌های اصلی

- Chat فارسی و انگلیسی با context مکالمه و حافظه پایدار
- تشخیص معنایی درخواست‌ها بدون وابستگی به عبارت‌های ثابت
- استخراج نیازمندی‌ها و معیارهای پذیرش از درخواست
- برنامه‌ریزی معماری و مراحل اجرای پروژه قبل از کدنویسی
- استفاده ترکیبی از دانش آموزشی داخلی و تحقیق وب
- تولید مرحله‌ای پروژه بر اساس زبان و فناوری مناسب
- Build، test، lint و repair برای پروژه‌های تولیدشده
- اعتبارسنجی متناسب با نوع پروژه و محیط اجرا
- self-review و جلوگیری از اعلام موفقیت در صورت failure
- Git lifecycle برای workspace پروژه تولیدشده
- ادامه‌دادن کارهای چندمرحله‌ای بر اساس context قبلی
- یادگیری پیوسته و curriculum قابل توسعه
- بازیابی دانش مرتبط از حافظه محلی
- پردازش فایل‌های محلی و اتصال آن‌ها به مکالمه
- اجرای کنترل‌شده ابزارها و کد با permission و confirmation
- احراز هویت، authorization و audit log
- مدیریت CPU، RAM و GPU
- اجرای background worker و scheduler
- self-update و self-repair با کنترل دسترسی
- رابط وب محلی

## چرخه عمومی مهندسی نرم‌افزار

```text
User Request
    ↓
Semantic Understanding + Context
    ↓
Requirements + Acceptance Criteria
    ↓
Local Knowledge + Web Research
    ↓
Technical Decisions + Architecture
    ↓
Project Plan
    ↓
Implementation
    ↓
Build / Run
    ↓
Tests + Runtime Validation
    ↓
Failure Analysis → Research / Repair → Retest
    ↓
Self Review
    ↓
Workspace Cleanup + Git Commit
    ↓
Evidence-based Completion Report
```

جزئیات این lifecycle در `docs/PROJECT_DOCUMENTATION.md` مستند شده است.

## معماری کلی

```text
User Request
    ↓
Semantic Router
    ↓
Conversation Context + Persistent Memory
    ↓
Software Planning Agent
    ├── Requirements
    ├── Knowledge Retrieval
    ├── Web Research
    └── Architecture / Validation Plan
    ↓
Implementation Agent
    ↓
Build → Test → Runtime Validation → Repair
    ↓
Self Review → Git → Response
```

## مدل و Runtime

پیکربندی اصلی از طریق متغیرهای محیطی انجام می‌شود، از جمله:

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `ROUTER_MODEL`
- `CODING_MODEL`
- `FALLBACK_MODEL`
- `EMBEDDING_MODEL`
- `OLLAMA_NUM_CTX`
- `OLLAMA_NUM_THREAD`
- `OLLAMA_KEEP_ALIVE`

اجرای CPU-only پشتیبانی می‌شود و GPU اختیاری است.

## یادگیری

سیستم یادگیری شامل انتخاب موضوع، کشف پیش‌نیازها، دریافت منابع، استخراج دانش، ساخت درس و تمرین، ارزیابی، ثبت progress و review دوره‌ای است.

هر domain می‌تواند curriculum مستقل داشته باشد و منابع رسمی، مستندات اکوسیستم، release notes، استانداردها و منابع تکمیلی مرتبط با همان domain را دریافت کند.

پس از تکمیل یک domain، review دوره‌ای می‌تواند تغییرات جدید را بررسی کرده و مطالب جدید را بدون حذف دانش قبلی اضافه کند.

## حافظه و Context

My-AI وضعیت مکالمه و دانش مرتبط را در SQLite نگهداری می‌کند و هنگام پاسخ‌گویی یا تولید پروژه می‌تواند از موارد مرتبط قبلی استفاده کند.

تشخیص کار بر اساس معنی درخواست و وضعیت مکالمه انجام می‌شود؛ عبارت‌های متفاوتی که یک هدف یکسان دارند نباید نیازمند triggerهای جداگانه باشند.

## تولید پروژه

برای درخواست‌های نرم‌افزاری، runtime ابتدا intent را به‌صورت معنایی تشخیص می‌دهد. سپس Planning Agent نیازمندی‌ها، معماری، معیارهای پذیرش و validation را استخراج می‌کند. Research Agent دانش داخلی و منابع وب مرتبط را جمع می‌کند و Implementation Agent بر اساس آن‌ها پروژه را می‌سازد.

پروژه تا حد امکان build، test، lint و runtime validation می‌شود. خطاها وارد repair loop می‌شوند و فقط پس از عبور از معیارهای واقعی completion، نتیجه کامل اعلام می‌شود.

برای فناوری‌هایی که ابزار validation آن‌ها روی سیستم موجود نیست، وضعیت `unavailable`/`blocked` گزارش می‌شود و به‌اشتباه موفقیت اعلام نمی‌شود.

## امنیت و کنترل دسترسی

پروژه دارای authentication، authorization، permissionهای ابزار، confirmation برای عملیات حساس و audit logging است. قابلیت‌های عملیاتی بر اساس permission و policy کنترل می‌شوند.

## Git و GitHub

My-AI می‌تواند با repositoryهای Git/GitHub کار کند. برای پروژه‌های تولیدشده، lifecycle Git در همان workspace انجام می‌شود و repository اصلی My-AI بدون مجوز تغییر نمی‌کند.

## توسعه و تست

تست‌های پروژه با `pytest` اجرا می‌شوند. CI بررسی‌های compile، lint، type checking، dependency audit و container build را انجام می‌دهد.

برای توسعه محلی:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

برای سناریوهای پذیرش Agent، `tests/test_software_agent.py` و `docs/PROJECT_DOCUMENTATION.md` را بررسی کنید.

## ساختار کلی

```text
my_ai/
  agent.py
  agent_runtime.py
  software_agent.py
  domain/
  learning/
  project_builder.py
  project_workspace.py
  memory.py
  db.py
  scheduler.py
  auth.py
  api.py
  static/

tests/
docs/
requirements.lock
Dockerfile
docker-compose.yml
```

## مجوز

این پروژه تحت مجوز MIT منتشر شده است.


## Advanced Agent Maturity Roadmap

See `docs/ADVANCED_AGENT_MATURITY_ROADMAP.md` for the registered roadmap and acceptance standard.
