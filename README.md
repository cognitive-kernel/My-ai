# My-AI — Personal Local Learning Agent

My-AI is a **zero-cost, local-first AI learning and coding agent** designed for a normal computer (for example, Intel Core i5 + 32 GB RAM + integrated graphics). It uses a locally hosted LLM through Ollama, persistent SQLite memory, web learning, a Python curriculum, code execution, evaluation, and project-oriented task planning.

> The project does not train an LLM from scratch. It builds a persistent learning/agent layer around a local model. The model can be replaced later without losing the knowledge database.

## فارسی

**My-AI** یک عامل هوش مصنوعی شخصی و محلی است که برای اجرای رایگان روی سیستم معمولی طراحی شده است؛ مثلاً Core i5 با 32GB RAM و گرافیک آنبرد.

امکانات اصلی:
- اجرای مدل زبانی به‌صورت محلی با Ollama و بدون هزینه API.
- چت و حافظه دائمی با SQLite.
- یادگیری مرحله‌ای Python از منابع اینترنتی.
- ذخیره دانش آموخته‌شده در حافظه قابل جست‌وجو.
- اجرای کد Python و بررسی نتیجه.
- برنامه درسی و آزمون برای Python.
- جمع‌آوری محتوای وب بدون نیاز به API پولی.
- ثبت تجربه‌ها، خطاها و نتایج یادگیری.
- تعریف پروژه و تبدیل آن به وظایف مرحله‌ای.
- API محلی با FastAPI.
- امکان تعویض مدل بدون از دست دادن حافظه.
- تست خودکار و CI.

### نکته مهم
این پروژه «آموزش مجدد مدل زبانی از صفر» نیست. مدل محلی نقش موتور استدلال و تولید متن را دارد و My-AI لایه حافظه، مطالعه، تمرین، اجرا و ارزیابی را به آن اضافه می‌کند.

## Architecture

```
User
  |
  v
FastAPI
  |
  +--> Local LLM (Ollama)
  |
  +--> SQLite memory / knowledge
  |
  +--> Web learner
  |
  +--> Python executor
  |
  +--> Curriculum + evaluator
  |
  +--> Project planner
```

## Features

### 1. Local LLM
Default provider is Ollama. No paid API key is required.

Recommended starting model for 32 GB RAM:
- A small coding-capable 7B/8B quantized model.

The exact model is configurable through `OLLAMA_MODEL`.

### 2. Persistent memory
The database stores:
- conversations
- knowledge items
- learning sessions
- experiments
- project tasks

### 3. Python learning
The built-in curriculum starts with:
1. syntax and execution
2. variables and types
3. control flow
4. functions
5. collections
6. modules and packages
7. exceptions
8. files
9. OOP
10. typing
11. testing
12. async programming
13. databases
14. HTTP/API development
15. packaging and deployment
16. security and production practices

The learner can study a source, summarize it, store knowledge, create an exercise, execute the solution, and record the result.

### 4. Web learning
The learner can fetch public web pages using ordinary HTTP requests. It is intentionally conservative:
- respects HTTP errors
- limits downloaded content
- strips scripts/styles
- extracts readable text
- stores source URL with knowledge

Use only sources you are legally allowed to access.

### 5. Python execution
Code is executed with:
- timeout
- output-size limit
- temporary working directory
- isolated process

This is **not a perfect security sandbox**. Do not execute untrusted code on a machine containing sensitive data. Docker isolation can be added later.

### 6. Project mode
Send a project goal to `/projects/plan`. The planner creates structured tasks. Each task can then be handled by the local model and validated with tests.

## Installation

### 1. Requirements

- Python 3.11+
- Ollama
- 16 GB RAM minimum; 32 GB recommended
- Internet connection only for web learning/model download

### 2. Install Python dependencies

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Install and start Ollama

Install Ollama from its official installer, then download a suitable model:

```bash
ollama pull qwen2.5-coder:7b
```

If that exact tag is unavailable on your installation, set `OLLAMA_MODEL` to an available coding model.

### 4. Start My-AI

```bash
python -m my_ai
```

Open:
``http://127.0.0.1:8000/docs``

## API examples

### Chat

```bash
curl -X POST http://127.0.0.1:8000/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"Explain Python decorators\"}"
```

### Learn a web page

```bash
curl -X POST http://127.0.0.1:8000/learn/url ^
  -H "Content-Type: application/json" ^
  -d "{\"url\":\"https://docs.python.org/3/tutorial/\"}"
```

### Start Python learning

```bash
curl -X POST http://127.0.0.1:8000/learning/python/start
```

### Plan a project

```bash
curl -X POST http://127.0.0.1:8000/projects/plan ^
  -H "Content-Type: application/json" ^
  -d "{\"goal\":\"Build a FastAPI service with SQLite and tests\"}"
```

## Configuration

Environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama endpoint |
| `OLLAMA_MODEL` | `qwen2.5-coder:7b` | Local model |
| `DB_PATH` | `data/myai.db` | SQLite database |
| `MAX_WEB_CHARS` | `30000` | Maximum extracted web text |
| `EXEC_TIMEOUT` | `10` | Python execution timeout |
| `HOST` | `127.0.0.1` | API bind address |
| `PORT` | `8000` | API port |

## Testing

```bash
pytest -q
```

## English summary

My-AI is a local-first learning agent rather than a new foundation model. It combines a local LLM with persistent memory, web ingestion, curriculum management, Python execution, evaluation, and project planning. It is designed to be free to run after the local model is downloaded.

## Roadmap

- [x] Local LLM adapter
- [x] SQLite memory
- [x] Web ingestion
- [x] Python execution
- [x] Python curriculum
- [x] Learning sessions
- [x] Project planning
- [x] REST API
- [x] Automated tests
- [ ] Vector embeddings / semantic search
- [ ] Docker code sandbox
- [ ] Browser UI
- [ ] Scheduled autonomous study
- [ ] Multi-language curricula (C, C++, Rust, etc.)
- [ ] Long-running autonomous agent loop
