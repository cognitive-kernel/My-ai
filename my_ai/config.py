from __future__ import annotations
import os
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()
@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    db_path: str = os.getenv("DB_PATH", "data/myai.db")
    max_web_chars: int = int(os.getenv("MAX_WEB_CHARS", "30000"))
    exec_timeout: int = int(os.getenv("EXEC_TIMEOUT", "10"))
    exec_mode: str = os.getenv("EXECUTOR_MODE", "container").strip().lower()
    exec_memory: str = os.getenv("EXEC_MEMORY", "256m")
    exec_cpus: str = os.getenv("EXEC_CPUS", "1.0")
    exec_pids: int = int(os.getenv("EXEC_PIDS", "64"))
    exec_output_chars: int = int(os.getenv("EXEC_OUTPUT_CHARS", "12000"))
    exec_image: str = os.getenv("EXECUTOR_IMAGE", "python:3.11-slim")
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))
settings = Settings()
