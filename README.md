# My-AI — Personal Local Learning Agent

My-AI is a **zero-cost, local-first AI learning and coding agent** for an ordinary computer such as Core i5 + 32 GB RAM + integrated graphics. It uses a local LLM through Ollama, so the application itself does not require a paid AI subscription.

## فارسی

My-AI یک عامل هوش مصنوعی شخصی و محلی است. هدف پروژه این است که یک مدل زبانی محلی را با **حافظه دائمی، مطالعه منابع، برنامه آموزشی، تمرین، اجرای کد، ارزیابی، برنامه‌ریزی پروژه و یادگیری دوره‌ای** ترکیب کند.

### امکانات پیاده‌سازی‌شده
- مدل زبانی محلی با Ollama.
- چت وب و REST API.
- حافظه مکالمه.
- حافظه دانش دائمی SQLite.
- جست‌وجوی متنی سریع با SQLite FTS5.
- مطالعه صفحات عمومی وب و ثبت منبع.
- محافظت پایه در برابر دسترسی Web Learner به IPهای خصوصی/لوکال.
- دوره آموزشی Python.
- دوره آموزشی C.
- گام‌های یادگیری خودکار و امتیازدهی اولیه.
- تولید تمرین.
- اجرای محدود Python با timeout و محدودیت خروجی.
- برنامه‌ریزی پروژه و معیار پذیرش.
- Scheduler برای مطالعه دوره‌ای.
- رابط وب ساده.
- Docker و docker-compose.
- تست‌های خودکار و GitHub Actions.
- معماری ماژولار برای مدل‌ها و زبان‌های بیشتر.

### نحوه «یادگیری»
این پروژه وزن‌های مدل را از صفر آموزش نمی‌دهد. مدل محلی موتور استدلال است و My-AI اطلاعات، یادداشت‌ها، منابع، مکالمات و نتایج را در حافظه نگه می‌دارد و در درخواست‌های بعدی بازیابی می‌کند. بنابراین با گذشت زمان **دانش قابل بازیابی و تجربه ثبت‌شده** افزایش می‌یابد.

### نکته امنیتی
اجرای Python با subprocess یک sandbox امنیتی کامل نیست. برای اجرای کد کاملاً غیرقابل اعتماد، باید executor کانتینری/VM واقعی اضافه شود. Web Learner نیز فقط درخواست‌های عمومی را اجازه می‌دهد و IPهای خصوصی/loopback را مسدود می‌کند.

## English

My-AI is a **zero-cost, local-first personal AI learning and coding agent**. It combines a locally hosted LLM with persistent memory, searchable knowledge, web ingestion, curricula, exercises, bounded code execution, project planning and scheduled learning.

### Implemented capabilities
- Local Ollama LLM.
- Web UI and REST API.
- Persistent conversation memory.
- SQLite knowledge storage.
- SQLite FTS5 retrieval.
- Public web-page ingestion with source attribution.
- Basic SSRF protection for private/loopback destinations.
- Python curriculum.
- C curriculum.
- Autonomous learning steps with basic assessment.
- Exercise generation.
- Bounded Python execution with timeout/output limits.
- Project planning with acceptance criteria.
- Periodic study scheduler.
- Docker deployment.
- Automated tests and GitHub Actions.
- Modular architecture for additional models/languages.

### Learning model
My-AI does **not** retrain a foundation model from scratch. The local LLM remains the reasoning engine. My-AI builds a persistent external memory and learning workflow around it: sources are processed, notes are stored, exercises can be generated, code can be executed, and results can be recorded for future retrieval.

## Architecture

User
  |
  v
Web UI / REST API
  |
  v
Agent -----> Ollama local LLM
  |
  +----> SQLite + FTS5 memory
  +----> Web learner
  +----> Curriculum
  +----> Python executor
  +----> Learning scheduler
  +----> Project planner

## Installation

Requirements:
- Python 3.11+
- Ollama
- 16 GB RAM minimum; 32 GB recommended
- Internet only for model download and web learning

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# Linux/macOS:
# source .venv/bin/activate
pip install -r requirements.txt
ollama pull qwen2.5-coder:7b
python -m my_ai
```

Open `http://127.0.0.1:8000` or `/docs`.

## Main API

- `POST /chat`
- `POST /learn/url`
- `POST /learning/start`
- `POST /learning/step`
- `GET /learning/status`
- `POST /learning/practice`
- `POST /code/run`
- `POST /projects/plan`
- `GET /memory/search?q=...`
- `GET /memory/knowledge`
- `GET /projects/tasks`
- `POST /scheduler/start`
- `POST /scheduler/stop`

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| OLLAMA_BASE_URL | http://127.0.0.1:11434 | Ollama endpoint |
| OLLAMA_MODEL | qwen2.5-coder:7b | Local model |
| DB_PATH | data/myai.db | Persistent database |
| MAX_WEB_CHARS | 30000 | Maximum extracted page text |
| EXEC_TIMEOUT | 10 | Python execution timeout |
| HOST | 127.0.0.1 | API bind address |
| PORT | 8000 | API port |

## Tests

```bash
pytest -q
```

## Scope of this release

The **core project is implemented**. It is not a claim that a small local model will have the same reasoning ability as a commercial frontier model, nor that external memory equals model-weight training. Those are separate technical capabilities.

Optional future upgrades can improve semantic retrieval, sandboxing, browser UX, autonomous multi-step project execution, Git integration and fine-tuning.
