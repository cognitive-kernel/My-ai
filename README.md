# My-AI — Local Personal AI Assistant

My-AI is a local-first personal AI assistant built around Ollama. After installation, the main remaining activity is **telling it what to learn**; the application handles the learning workflow, persistent knowledge, progress tracking and later code generation.

## What is included

### Assistant
- Local LLM through Ollama.
- Persistent conversation memory.
- Knowledge memory with SQLite + FTS5 retrieval.
- Context-aware answers using conversation and learned knowledge.
- Project planning with tasks and acceptance criteria.
- Python code generation and validation.
- REST API and browser dashboard.
- Persian web chat.
- Browser voice input (microphone) and Persian text-to-speech.
- Health and scheduler status endpoints.

### Autonomous learning
Tell the assistant in chat, for example:
- «پایتون را یاد بگیر»
- «PHP را یاد بگیر»
- «C را یاد بگیر»
- «JavaScript را یاد بگیر»
- «SQL Server را یاد بگیر»
- «MySQL را یاد بگیر»
- «SQLite را یاد بگیر»
- «Android را یاد بگیر»
- «iOS را یاد بگیر»

Or call `POST /learning/learn`. The scheduler then:
1. selects the next unfinished curriculum topic;
2. fetches official/reference documentation;
3. extracts topic-relevant knowledge with the local model;
4. stores the source and durable notes in SQLite;
5. creates a lesson, examples, exercises and mastery checklist;
6. assesses the lesson;
7. records progress;
8. continues with the next topic on the configured interval.

The dashboard shows completed topics, total topics, percentage progress and average assessment.

Current built-in learning tracks: **Python, C, PHP, JavaScript, SQL Server/T-SQL, MySQL, SQLite, Android/Kotlin and iOS/Swift**.

Database learning is a first-class part of the curriculum. The Android track covers SQLite/Room and the iOS track covers Core Data/SQLite; application-integration topics also connect SQL Server/MySQL/SQLite with Python, PHP and JavaScript.

### Coding after learning
A chat command such as «برای من یک برنامه مدیریت فایل با پایتون بنویس» is routed to the coding engine. The engine retrieves learned knowledge, generates source code and, for Python, runs a bounded validation step.

Important: Python execution is an execution utility, not a strong security sandbox. Do not run untrusted code. For hostile/untrusted generated code, use container/VM isolation.

## Voice

The web UI uses browser speech capabilities:
- Speech recognition: `SpeechRecognition` / `webkitSpeechRecognition`
- Speech synthesis: `speechSynthesis`
- Persian locale: `fa-IR`

Microphone permission and browser support are required. The AI model itself remains local in Ollama.

## Architecture

Web UI / Voice
       |
       v
FastAPI
       |
       +--> Command Router / Agent
       |       +--> Chat
       |       +--> Learning
       |       +--> Code generation
       |       +--> Project planning
       |
       +--> Ollama local LLM
       +--> SQLite + FTS5 memory
       +--> Official web sources
       +--> Python executor
       +--> Learning scheduler

## Installation

Requirements:
- Python 3.11+
- Ollama
- Internet connection for downloading the model and learning from public documentation
- 16 GB RAM minimum; 32 GB recommended

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull qwen2.5-coder:7b
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

Open `http://127.0.0.1:8000`.

## Main API

- `POST /chat`
- `POST /code/generate`
- `POST /code/run`
- `POST /learn/url`
- `POST /learning/start`
- `POST /learning/step`
- `POST /learning/learn` — start continuous learning
- `GET /learning/status`
- `POST /learning/practice`
- `POST /projects/plan`
- `GET /projects/tasks`
- `GET /memory/search?q=...`
- `GET /memory/knowledge`
- `POST /scheduler/start`
- `GET /scheduler/status`
- `POST /scheduler/stop`

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| OLLAMA_BASE_URL | http://127.0.0.1:11434 | Ollama endpoint |
| OLLAMA_MODEL | qwen2.5-coder:7b | Local model |
| DB_PATH | data/myai.db | Persistent database |
| MAX_WEB_CHARS | 30000 | Maximum extracted web text |
| EXEC_TIMEOUT | 10 | Python execution timeout |
| HOST | 127.0.0.1 | API bind address |
| PORT | 8000 | API port |

## Learning progress

The percentage is currently calculated from curriculum completion:
`completed topics / total topics * 100`.

The assessment score is tracked separately. This avoids falsely claiming that a language is "100% mastered" merely because the model completed a lesson sequence. A future mastery model can combine exercises, tests and repeated assessments.

## Important technical boundary

This project does **not** retrain foundation-model weights. The local model is the reasoning engine; My-AI provides persistent external memory, source ingestion, curriculum, exercises, assessment, execution and project workflows.

That design is intentional for ordinary hardware. It allows the assistant to accumulate useful project-specific knowledge without requiring GPU training.

## Final verification

After pulling the repository, run:

```bash
pip install -e .
pytest -q
```

Then verify:
1. Ollama responds.
2. `http://127.0.0.1:8000` opens.
3. Microphone permission works.
4. «پایتون را یاد بگیر» starts a learning session.
5. «SQL Server را یاد بگیر» starts the SQL Server track.
6. «MySQL را یاد بگیر» starts the MySQL track.
7. «SQLite را یاد بگیر» starts the SQLite track.
8. «Android را یاد بگیر» starts the Android/Kotlin track.
9. «iOS را یاد بگیر» starts the iOS/Swift track.
10. The dashboard changes after a completed topic.
11. A coding request for a selected language returns source code.

CI runs the automated test suite on pushes and pull requests.
