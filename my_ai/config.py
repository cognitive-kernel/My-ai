from __future__ import annotations

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv
load_dotenv()

@dataclass(frozen=True)
class Settings:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    ollama_num_ctx: int = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
    ollama_num_thread: int = int(os.getenv("OLLAMA_NUM_THREAD", "8"))
    ollama_num_gpu: int = int(os.getenv("OLLAMA_NUM_GPU", "0"))
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "10m")
    routing_model: str = os.getenv("ROUTER_MODEL", "qwen2.5:7b")
    router_llm_enabled: bool = os.getenv("ROUTER_LLM_ENABLED", "true").strip().lower() == "true"
    coding_model: str = os.getenv("CODING_MODEL", "qwen2.5:7b")
    fallback_model: str = os.getenv("FALLBACK_MODEL", "qwen2.5:7b")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
    knowledge_duplicate_threshold: float = float(os.getenv("KNOWLEDGE_DUPLICATE_THRESHOLD", "0.92"))
    cache_ttl_seconds: int = int(os.getenv("MYAI_CACHE_TTL", "60"))
    llm_provider: str = os.getenv("LLM_PROVIDER", "auto").strip().lower()
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "data/myai.db"))
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
    offline_strict: bool = os.getenv("MYAI_OFFLINE_STRICT", "false").strip().lower() == "true"
    read_only: bool = os.getenv("MYAI_READ_ONLY", "false").strip().lower() == "true"
    decision_log: bool = os.getenv("MYAI_DECISION_LOG", "false").strip().lower() == "true"
    scheduler_interval_seconds: int = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "3600"))
    scheduler_max_cpu_percent: float = float(os.getenv("SCHEDULER_MAX_CPU_PERCENT", "70"))
    scheduler_max_ram_percent: float = float(os.getenv("SCHEDULER_MAX_RAM_PERCENT", "80"))
    scheduler_auto_resume: bool = os.getenv("SCHEDULER_AUTO_RESUME", "false").strip().lower() == "true"
    learning_max_retries: int = int(os.getenv("LEARNING_MAX_RETRIES", "5"))
    learning_max_concurrent_workers: int = max(1, int(os.getenv("LEARNING_MAX_CONCURRENT_WORKERS", "2")))
    learning_source_timeout_seconds: float = float(os.getenv("LEARNING_SOURCE_TIMEOUT_SECONDS", "8"))
    learning_source_max_chars: int = max(1000, int(os.getenv("LEARNING_SOURCE_MAX_CHARS", "12000")))
    resource_wait_seconds: float = max(1.0, float(os.getenv("RESOURCE_WAIT_SECONDS", "30")))

settings = Settings()



def assert_write_allowed(path: str) -> None:
    from .access_policy import assert_mutation_allowed
    assert_mutation_allowed(str(path))
