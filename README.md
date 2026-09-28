# My-AI — Local Personal AI Assistant

My-AI is a **local-first personal AI assistant** built around Ollama, FastAPI and SQLite. It provides natural-language chat, persistent memory, continuous learning, code and project generation, controlled code execution, Git/GitHub integration, documentation help, voice, local-file processing, resource control, self-update and self-repair.

این پروژه یک دستیار هوش مصنوعی **local-first** است که مدل را به‌صورت محلی اجرا می‌کند و برای گفتگو، یادگیری، درک context، تولید کد و پروژه، اجرای کنترل‌شده کد، کار با Git/GitHub، پردازش فایل و مدیریت منابع طراحی شده است.

## قابلیت‌های اصلی

- Chat فارسی و انگلیسی با context مکالمه و حافظه پایدار
- تشخیص معنایی درخواست‌ها بدون وابستگی به عبارت‌های ثابت
- تولید کد و پروژه بر اساس هدف، زبان و مشخصات درخواست
- ادامه‌دادن کارهای چندمرحله‌ای بر اساس context قبلی
- ساخت فایل‌ها و پروژه‌ها در workspace مشخص
- Build، test، lint و repair برای پروژه‌های تولیدشده
- Git/GitHub integration
- یادگیری پیوسته و curriculum قابل توسعه
- بازیابی دانش مرتبط از حافظه محلی
- پردازش فایل‌های محلی و اتصال آن‌ها به مکالمه
- اجرای کنترل‌شده ابزارها و کد با permission و confirmation
- احراز هویت، authorization و audit log
- مدیریت CPU، RAM و GPU
- اجرای background worker و scheduler
- self-update و self-repair با کنترل دسترسی
- رابط وب محلی

## معماری کلی

```text
User Request
    ↓
Semantic Router
    ↓
Conversation Context + Persistent Memory
    ↓
Agent Runtime
    ↓
Task Planning / Knowledge Retrieval / Tool Selection
    ↓
Code & Project Generation
    ↓
Build → Test → Lint → Repair
    ↓
Workspace / Git / Response
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

این معماری برای درخواست‌هایی طراحی شده که ممکن است در چند پیام و با بیان‌های متفاوت مطرح شوند؛ تشخیص کار بر اساس معنای درخواست و وضعیت مکالمه انجام می‌شود، نه صرفاً تطبیق چند کلمه مشخص.

## تولید پروژه

برای درخواست‌های برنامه‌نویسی، runtime ابتدا هدف و نوع کار را تشخیص می‌دهد، زبان و context مرتبط را استخراج می‌کند، سپس artifactهای موردنیاز را ایجاد می‌کند و در صورت امکان آن‌ها را build، test و lint می‌کند.

مسیر workspace پروژه‌ها قابل تنظیم است و نتیجه عملیات همراه با وضعیت build/test/lint گزارش می‌شود.

## امنیت و کنترل دسترسی

پروژه دارای authentication، authorization، permissionهای ابزار، confirmation برای عملیات حساس و audit logging است. قابلیت‌های عملیاتی بر اساس permission و policy کنترل می‌شوند.

## Git و GitHub

پروژه می‌تواند با repositoryهای Git/GitHub کار کند و عملیات تغییر، بررسی و نگهداری پروژه را از طریق ابزارهای کنترل‌شده انجام دهد.

## توسعه و تست

تست‌های پروژه با `pytest` اجرا می‌شوند. CI همچنین بررسی‌های compile، lint، type checking، dependency audit و container build را انجام می‌دهد.

برای توسعه محلی:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## ساختار کلی

```text
my_ai/
  agent.py
  agent_runtime.py
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
