from __future__ import annotations

import base64
import logging
import os
import secrets
from pathlib import Path
from typing import Any
SETTING_REGISTRY: dict[str, dict[str, Any]] = {
    "logging.level": {"version": 1, "type": "enum", "default": "WARNING", "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], "description": "Minimum console log level."},
    "learning.interval_seconds": {"version": 1, "type": "int", "default": 3600, "min": 60, "max": 86400, "description": "Learning interval in seconds."},
    "learning.max_retries": {"version": 1, "type": "int", "default": 5, "min": 1, "max": 20, "description": "Maximum learning retries."},
    "resources.cpu_percent": {"version": 1, "type": "float", "default": 70.0, "min": 1.0, "max": 100.0, "description": "Maximum CPU percentage."},
    "resources.cpu_threads": {"version": 1, "type": "int", "default": 8, "min": 1, "max": 128, "description": "Maximum CPU threads."},
    "resources.ram_percent": {"version": 1, "type": "float", "default": 80.0, "min": 1.0, "max": 100.0, "description": "Maximum RAM percentage."},
    "resources.gpu_layers": {"version": 1, "type": "int", "default": 0, "min": 0, "max": 128, "description": "GPU layers."},
    "llm.provider": {"version": 1, "type": "enum", "default": "auto", "choices": ["auto", "ollama", "openai-compatible", "custom-openai-compatible"], "description": "Active LLM provider."},
    "llm.retry_attempts": {"version": 1, "type": "int", "default": 2, "min": 1, "max": 5, "description": "LLM retry attempts."},
    "llm.timeout_seconds": {"version": 1, "type": "float", "default": 300.0, "min": 1.0, "max": 3600.0, "description": "LLM timeout in seconds."},
    "llm.custom.provider": {"version": 1, "type": "enum", "default": "openai-compatible", "choices": ["openai-compatible"], "description": "Protocol used by the custom LLM provider."},
    "llm.custom.base_url": {"version": 1, "type": "text", "default": "", "max_length": 1000, "description": "Base URL for a custom OpenAI-compatible LLM endpoint."},
    "llm.custom.model": {"version": 1, "type": "text", "default": "", "max_length": 300, "description": "Model ID exposed by the custom LLM provider."},
    "llm.custom.api_key": {"version": 1, "type": "text", "default": "", "max_length": 10000, "secret": True, "description": "API key for the custom LLM provider."},
    "learning.max_concurrent_workers": {"version": 1, "type": "int", "default": 2, "min": 1, "max": 16, "description": "Maximum concurrent learning workers."},
    "learning.source_timeout_seconds": {"version": 1, "type": "float", "default": 8.0, "min": 1.0, "max": 300.0, "description": "Learning source timeout."},
    "learning.source_max_chars": {"version": 1, "type": "int", "default": 12000, "min": 1000, "max": 200000, "description": "Maximum source characters retained."},
    "scheduler.interval_seconds": {"version": 1, "type": "int", "default": 3600, "min": 60, "max": 86400, "description": "Scheduler interval."},
    "scheduler.auto_resume": {"version": 1, "type": "enum", "default": "false", "choices": ["true", "false"], "description": "Automatically resume learning workers."},
    "execution.timeout_seconds": {"version": 1, "type": "int", "default": 10, "min": 1, "max": 3600, "description": "Execution timeout."},
    "learning.personal_experience": {"version": 1, "type": "enum", "default": "true", "choices": ["true", "false"], "description": "Store personal learning experiences."},
}

SETTING_REGISTRY.update({
    "agent.system_behavior": {"version": 2, "type": "text", "default": "", "max_length": 20000, "description": "System behavior policy."},
    "agent.persona": {"version": 2, "type": "text", "default": "", "max_length": 10000, "description": "Agent persona and role."},
    "agent.planning_strategy": {"version": 2, "type": "enum", "default": "adaptive", "choices": ["reactive","plan-execute","adaptive","graph"], "description": "Planning strategy."},
    "agent.max_steps": {"version": 2, "type": "int", "default": 20, "min": 1, "max": 1000, "description": "Maximum agent steps."},
    "agent.execution_timeout": {"version": 2, "type": "float", "default": 300, "min": 1, "max": 86400, "description": "Agent execution timeout."},
    "agent.cancellation_policy": {"version": 2, "type": "enum", "default": "cooperative", "choices": ["cooperative","immediate","checkpoint"], "description": "Cancellation policy."},
    "agent.trace_enabled": {"version": 2, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Execution tracing."},
    "tools.default_timeout": {"version": 2, "type": "float", "default": 30, "min": 0.1, "max": 3600, "description": "Default tool timeout."},
    "tools.default_retries": {"version": 2, "type": "int", "default": 2, "min": 0, "max": 20, "description": "Default tool retries."},
    "tools.unknown_policy": {"version": 2, "type": "enum", "default": "deny", "choices": ["deny","approval","allow"], "description": "Unknown tool policy."},
    "memory.backend": {"version": 2, "type": "enum", "default": "sqlite", "choices": ["sqlite","file","hybrid"], "description": "Memory backend."},
    "memory.retention_days": {"version": 2, "type": "int", "default": 365, "min": 1, "max": 36500, "description": "Memory retention."},
    "memory.duplicate_threshold": {"version": 2, "type": "float", "default": 0.92, "min": 0, "max": 1, "description": "Duplicate threshold."},
    "memory.chunk_size": {"version": 2, "type": "int", "default": 1000, "min": 100, "max": 100000, "description": "Knowledge chunk size."},
    "memory.chunk_overlap": {"version": 2, "type": "int", "default": 100, "min": 0, "max": 10000, "description": "Knowledge chunk overlap."},
    "memory.embedding_model": {"version": 2, "type": "text", "default": "", "max_length": 300, "description": "Embedding model."},
    "research.source_timeout": {"version": 2, "type": "float", "default": 15, "min": 1, "max": 600, "description": "Research source timeout."},
    "research.search_provider": {"version": 3, "type": "enum", "default": "duckduckgo-html", "choices": ["duckduckgo-html"], "description": "Research search provider."},
    "research.domain_allowlist": {"version": 3, "type": "text", "default": "", "max_length": 20000, "description": "Comma-separated allowed research domains."},
    "research.domain_denylist": {"version": 3, "type": "text", "default": "", "max_length": 20000, "description": "Comma-separated denied research domains."},
    "research.source_rank": {"version": 3, "type": "text", "default": "official,docs,academic,other", "max_length": 1000, "description": "Source ranking classes."},
    "research.max_content_chars": {"version": 2, "type": "int", "default": 30000, "min": 1000, "max": 1000000, "description": "Maximum research content."},
    "research.require_approval": {"version": 2, "type": "enum", "default": "false", "choices": ["true","false"], "description": "Require source approval."},
    "research.freshness_days": {"version": 2, "type": "int", "default": 30, "min": 0, "max": 36500, "description": "Freshness window."},
    "security.require_approval_sensitive": {"version": 2, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Approval for sensitive operations."},
    "security.network_default": {"version": 2, "type": "enum", "default": "deny", "choices": ["deny","allow","approval"], "description": "Default network policy."},
    "security.filesystem_default": {"version": 2, "type": "enum", "default": "sandbox", "choices": ["deny","sandbox","allow"], "description": "Default filesystem policy."},
    "security.subprocess_default": {"version": 2, "type": "enum", "default": "deny", "choices": ["deny","sandbox","allow"], "description": "Default subprocess policy."},
    "security.self_modification": {"version": 2, "type": "enum", "default": "approval", "choices": ["deny","approval","allow"], "description": "Self modification policy."},
    "self_update.require_approval": {"version": 2, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Self update approval."},
    "self_update.snapshot_before_apply": {"version": 2, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Snapshot before update."},
    "self_update.rollback_on_failure": {"version": 2, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Rollback on failed update."},
    "self_repair.require_approval": {"version": 2, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Self repair approval."},
    "scheduler.worker_count": {"version": 2, "type": "int", "default": 2, "min": 1, "max": 128, "description": "Scheduler worker count."},
    "scheduler.concurrency": {"version": 2, "type": "int", "default": 2, "min": 1, "max": 128, "description": "Scheduler concurrency."},
    "scheduler.default_priority": {"version": 2, "type": "int", "default": 100, "min": 0, "max": 100000, "description": "Default job priority."},
    "scheduler.retry_backoff": {"version": 2, "type": "float", "default": 5, "min": 0, "max": 86400, "description": "Scheduler retry backoff."},
    "execution.mode": {"version": 2, "type": "enum", "default": "local", "choices": ["local","sandbox","container"], "description": "Execution mode."},
    "execution.max_output_chars": {"version": 2, "type": "int", "default": 50000, "min": 1000, "max": 10000000, "description": "Execution output limit."},
    "execution.max_memory_mb": {"version": 2, "type": "int", "default": 2048, "min": 64, "max": 1048576, "description": "Execution memory limit."},
    "execution.max_cpu_seconds": {"version": 2, "type": "int", "default": 300, "min": 1, "max": 86400, "description": "Execution CPU limit."},
    "execution.cpu_cores": {"version": 3, "type": "float", "default": 1.0, "min": 0.1, "max": 128, "description": "Execution CPU core limit."},
    "server.session_timeout": {"version": 2, "type": "int", "default": 3600, "min": 60, "max": 86400, "description": "Session timeout."},
    "server.upload_limit_mb": {"version": 2, "type": "int", "default": 50, "min": 1, "max": 2048, "description": "Upload limit."},
    "server.request_timeout": {"version": 2, "type": "float", "default": 60, "min": 1, "max": 3600, "description": "Request timeout."},
    "server.rate_limit_per_minute": {"version": 2, "type": "int", "default": 120, "min": 1, "max": 100000, "description": "Rate limit."},
    "server.maintenance_mode": {"version": 2, "type": "enum", "default": "false", "choices": ["true","false"], "description": "Maintenance/read-only mode."},
    "server.host": {"version": 2, "type": "text", "default": "127.0.0.1", "max_length": 255, "description": "API bind host; applied on process restart."},
    "server.port": {"version": 2, "type": "int", "default": 8000, "min": 1, "max": 65535, "description": "API bind port; applied on process restart."},
    "server.cors_origins": {"version": 2, "type": "text", "default": "", "max_length": 10000, "description": "Allowed CORS origins."},
    "server.readiness_policy": {"version": 2, "type": "enum", "default": "strict", "choices": ["strict","degraded","permissive"], "description": "Readiness policy."},
    "server.notification_webhook": {"version": 2, "type": "text", "default": "", "max_length": 2000, "secret": True, "description": "Notification webhook secret URL."},
    "observability.telemetry_enabled": {"version": 2, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Telemetry enabled."},
    "observability.metrics_retention_days": {"version": 2, "type": "int", "default": 30, "min": 1, "max": 3650, "description": "Metrics retention."},
    "observability.trace_retention_days": {"version": 2, "type": "int", "default": 7, "min": 1, "max": 3650, "description": "Trace retention."},
    "database.backup_schedule": {"version": 2, "type": "text", "default": "daily", "max_length": 120, "description": "Backup schedule."},
    "database.backup_retention": {"version": 2, "type": "int", "default": 14, "min": 1, "max": 3650, "description": "Backup retention days."},
    "database.backup_destination": {"version": 2, "type": "text", "default": "", "max_length": 1000, "description": "Backup destination."},
    "database.encryption_enabled": {"version": 2, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Backup encryption."},
    "evaluation.enabled": {"version": 2, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Agent evaluation."},
    "evaluation.baseline": {"version": 2, "type": "text", "default": "", "max_length": 200, "description": "Evaluation baseline."},
    "experience.revalidation_on_version_change": {"version": 2, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Revalidate experiences on version change."},
    "experience.current_version_priority": {"version": 2, "type": "float", "default": 2.0, "min": 0, "max": 100, "description": "Current-version experience retrieval weight."},
})


SETTING_REGISTRY.update({
    "llm.routing.default_task": {"version": 3, "type": "enum", "default": "general", "choices": ["general","chat","coding","reasoning","embedding","routing"], "description": "Default task class for model routing."},
    "llm.routing.cost_weight": {"version": 3, "type": "float", "default": 0.0, "min": 0, "max": 100, "description": "Relative cost weight used by model routing."},
    "llm.routing.latency_weight": {"version": 3, "type": "float", "default": 1.0, "min": 0, "max": 100, "description": "Relative latency weight used by model routing."},
    "llm.routing.availability_required": {"version": 3, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Require healthy models for automatic routing."},
    "learning.mode": {"version": 3, "type": "enum", "default": "auto", "choices": ["auto","manual","hybrid"], "description": "Learning source selection mode."},
    "learning.mastery_threshold": {"version": 3, "type": "float", "default": 0.8, "min": 0, "max": 1, "description": "Minimum mastery score."},
    "learning.review_interval_seconds": {"version": 3, "type": "int", "default": 604800, "min": 60, "max": 31536000, "description": "Learning review interval."},
    "learning.manual_source_priority": {"version": 3, "type": "float", "default": 2.0, "min": 0, "max": 100, "description": "Weight applied to manually supplied sources."},
    "learning.source_max_bytes": {"version": 3, "type": "int", "default": 26214400, "min": 1024, "max": 524288000, "description": "Maximum uploaded learning-source size in bytes."},
    "agent.early_exit_enabled": {"version": 3, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Allow verified early exit."},
    "agent.multi_agent_mode": {"version": 3, "type": "enum", "default": "adaptive", "choices": ["off","adaptive","always"], "description": "Multi-agent escalation policy."},
    "agent.verification_escalation": {"version": 3, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Escalate low-confidence verification."},
    "agent.context_budget_tokens": {"version": 3, "type": "int", "default": 16000, "min": 256, "max": 200000, "description": "Context planner token budget."},
    "agent.budget_steps": {"version": 3, "type": "int", "default": 20, "min": 1, "max": 1000, "description": "Task step budget."},
    "agent.budget_tokens": {"version": 3, "type": "int", "default": 16000, "min": 256, "max": 1000000, "description": "Task token budget."},
    "agent.budget_seconds": {"version": 3, "type": "int", "default": 300, "min": 1, "max": 86400, "description": "Task time budget."},
    "agent.budget_tool_calls": {"version": 3, "type": "int", "default": 20, "min": 0, "max": 10000, "description": "Task tool-call budget."},
    "agent.cache_ttl_seconds": {"version": 3, "type": "int", "default": 300, "min": 0, "max": 86400, "description": "Agent cache freshness."},
    "agent.cache_enabled": {"version": 3, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Enable version-aware agent caching."},
    "agent.events_enabled": {"version": 3, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Enable event-driven workflows."},
    "agent.events_retry_limit": {"version": 3, "type": "int", "default": 3, "min": 0, "max": 20, "description": "Event retry limit."},
    "agent.events_dead_letter": {"version": 3, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Enable dead-letter handling."},
    "research.require_freshness": {"version": 3, "type": "enum", "default": "false", "choices": ["true","false"], "description": "Require freshness checks for research sources."},
    "research.manual_first_policy": {"version": 3, "type": "enum", "default": "hybrid", "choices": ["manual-first","hybrid","auto-first"], "description": "Manual versus discovered source precedence."},
    "execution.project_root": {"version": 3, "type": "text", "default": "projects", "max_length": 1000, "description": "Validated project root."},
    "execution.max_processes": {"version": 3, "type": "int", "default": 32, "min": 1, "max": 1000, "description": "Maximum process count."},
    "execution.sandbox_enabled": {"version": 3, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Sandbox execution."},
    "scheduler.default_quota": {"version": 3, "type": "int", "default": 10, "min": 1, "max": 100000, "description": "Default per-user task quota."},
    "database.path": {"version": 3, "type": "text", "default": "data/my_ai.db", "max_length": 1000, "description": "Active database path; restart may be required to relocate it."},
    "server.feature_flags": {"version": 3, "type": "text", "default": "{}", "max_length": 20000, "description": "JSON feature flag map."},
    "server.health_policy": {"version": 3, "type": "enum", "default": "standard", "choices": ["standard","strict","minimal"], "description": "Health/readiness policy."},
    "observability.log_destination": {"version": 3, "type": "text", "default": "console", "max_length": 200, "description": "Log destination policy."},
    "observability.alerts_enabled": {"version": 3, "type": "enum", "default": "true", "choices": ["true","false"], "description": "Alert processing."},
    "multimodal.image_provider": {"version": 3, "type": "text", "default": "automatic1111", "max_length": 100, "description": "Image provider."},
    "multimodal.voice_provider": {"version": 3, "type": "text", "default": "local", "max_length": 100, "description": "Voice provider."},
})

CONFIG_SCHEMA_VERSION = 3

_RUNTIME_SETTING_ATTRS = {
    "llm.provider": "llm_provider",
    "llm.retry_attempts": "llm_retry_attempts",
    "llm.timeout_seconds": "llm_timeout_seconds",
    "memory.embedding_model": "embedding_model",
    "research.source_timeout": "research_source_timeout",
    "research.max_content_chars": "max_web_chars",
    "research.search_provider": "research_search_provider",
    "research.domain_allowlist": "research_domain_allowlist",
    "research.domain_denylist": "research_domain_denylist",
    "research.source_rank": "research_source_rank",
    "memory.backend": "memory_backend",
    "memory.retention_days": "memory_retention_days",
    "memory.chunk_size": "memory_chunk_size",
    "memory.chunk_overlap": "memory_chunk_overlap",
    "memory.duplicate_threshold": "knowledge_duplicate_threshold",
    "execution.timeout_seconds": "exec_timeout",
    "execution.mode": "exec_mode",
    "execution.max_output_chars": "exec_output_chars",
    "execution.max_memory_mb": "exec_memory_mb",
    "execution.max_processes": "exec_pids",
    "execution.cpu_cores": "exec_cpu_cores",
    "server.host": "host",
    "server.port": "port",
    "database.path": "db_path",
    "learning.max_retries": "learning_max_retries",
    "learning.max_concurrent_workers": "learning_max_concurrent_workers",
    "learning.source_timeout_seconds": "learning_source_timeout_seconds",
    "learning.source_max_chars": "learning_source_max_chars",
    "scheduler.interval_seconds": "scheduler_interval_seconds",
    "scheduler.auto_resume": "scheduler_auto_resume",
    "resources.cpu_percent": "scheduler_max_cpu_percent",
    "resources.ram_percent": "scheduler_max_ram_percent",
    "agent.cache_ttl_seconds": "cache_ttl_seconds",
}

def _coerce_runtime_value(current: Any, value: Any) -> Any:
    if isinstance(current, bool):
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(current, int) and not isinstance(current, bool):
        return int(value)
    if isinstance(current, float):
        return float(value)
    return str(value)

def apply_runtime_setting(key: str, value: Any) -> None:
    attr = _RUNTIME_SETTING_ATTRS.get(key)
    if not attr:
        return
    from .config import settings
    if not hasattr(settings, attr):
        return
    current = getattr(settings, attr)
    setattr(settings, attr, _coerce_runtime_value(current, value))

def apply_persisted_settings() -> None:
    ensure_schema()
    with connect() as conn:
        rows = conn.execute("SELECT key,value,secret FROM app_settings").fetchall()
    for row in rows:
        value = _decrypt(str(row["value"])) if int(row["secret"]) else str(row["value"])
        apply_runtime_setting(str(row["key"]), value)

def get_setting_registry() -> dict[str, dict[str, Any]]:
    result = {}
    for key, spec in SETTING_REGISTRY.items():
        item = dict(spec)
        item.setdefault("category", key.split(".", 1)[0])
        item.setdefault("depends_on", [])
        result[key] = item
    return result

def get_configuration_schema_version() -> int:
    return CONFIG_SCHEMA_VERSION

def migrate_configuration() -> int:
    ensure_schema()
    with connect() as conn:
        row = conn.execute("SELECT COALESCE(MAX(version), 0) AS version FROM app_settings_migrations").fetchone()
        current = int(row["version"]) if row else 0
        if current < CONFIG_SCHEMA_VERSION:
            conn.execute(
                "INSERT INTO app_settings_migrations(version, description) VALUES(?, ?)",
                (CONFIG_SCHEMA_VERSION, "Initial Configuration Registry schema."),
            )
            conn.commit()
        return CONFIG_SCHEMA_VERSION

def validate_registered_setting(key: str, value: Any) -> Any:
    meta = SETTING_REGISTRY.get(key)
    if not meta: raise KeyError(f"Unknown registered setting: {key}")
    kind = meta["type"]
    if kind == "int":
        try: value = int(value)
        except (TypeError, ValueError) as exc: raise ValueError(f"{key} must be integer") from exc
    elif kind == "float":
        try: value = float(value)
        except (TypeError, ValueError) as exc: raise ValueError(f"{key} must be number") from exc
    else: value = str(value)
    if meta.get("type") == "text" and len(value) > int(meta.get("max_length", 10000)): raise ValueError(f"{key} is too long")
    if "min" in meta and value < meta["min"]: raise ValueError(f"{key} below minimum")
    if "max" in meta and value > meta["max"]: raise ValueError(f"{key} above maximum")
    if "choices" in meta and value not in meta["choices"]: raise ValueError(f"{key} has invalid choice")
    dependencies = meta.get("depends_on", []) or []
    missing = [dep for dep in dependencies if not str(get_setting(str(dep), "") or "").strip()]
    if missing: raise ValueError(f"{key} requires settings: {\", \".join(missing)}")
    return value

def reset_setting(key: str) -> Any:
    meta = SETTING_REGISTRY.get(key)
    if not meta: raise KeyError(f"Unknown registered setting: {key}")
    delete_setting(key)
    return meta["default"]


from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .db import connect
from .access_policy import assert_mutation_allowed

ROOT = Path(__file__).resolve().parent.parent
KEY_PATH = ROOT / "data" / ".settings_key"
SECRET_PREFIX = "enc:v1:"
SCHEMA = """CREATE TABLE IF NOT EXISTS app_settings_history (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 key TEXT NOT NULL,
 old_value TEXT,
 new_value TEXT,
 schema_version INTEGER NOT NULL,
 changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS app_settings (
 key TEXT PRIMARY KEY,
 value TEXT NOT NULL,
 secret INTEGER NOT NULL DEFAULT 0,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 schema_version INTEGER NOT NULL DEFAULT 1
);"""

def _key() -> bytes:
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        raw = KEY_PATH.read_bytes()
    else:
        raw = secrets.token_bytes(32)
        KEY_PATH.write_bytes(raw)
        try:
            os.chmod(KEY_PATH, 0o600)
        except OSError as exc:
            logging.getLogger(__name__).debug("settings key chmod failed: %s", exc)
    if len(raw) != 32:
        raise RuntimeError("Invalid My-AI settings encryption key.")
    return raw

def _encrypt(value: str) -> str:
    nonce = os.urandom(12)
    data = AESGCM(_key()).encrypt(nonce, value.encode("utf-8"), b"my-ai-app-settings-v1")
    return SECRET_PREFIX + base64.b64encode(nonce + data).decode("ascii")

def _decrypt(value: str) -> str:
    if not value.startswith(SECRET_PREFIX):
        return value
    blob = base64.b64decode(value[len(SECRET_PREFIX):])
    if len(blob) < 13:
        raise ValueError("Invalid encrypted setting.")
    return AESGCM(_key()).decrypt(blob[:12], blob[12:], b"my-ai-app-settings-v1").decode("utf-8")

def ensure_schema() -> None:
    # Settings access is on a hot path, including the learning scheduler.
    # Do not run the full DB migration on every read: init_db() performs
    # multiple writes and can contend with learning/background transactions.
    with connect() as conn:
        conn.executescript(SCHEMA)
        columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(app_settings)").fetchall()}
        if "schema_version" not in columns:
            conn.execute("ALTER TABLE app_settings ADD COLUMN schema_version INTEGER NOT NULL DEFAULT 1")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                description TEXT NOT NULL
            )
        """)
        conn.commit()

def get_setting(key: str, default: Any = None, *, secret: bool = False) -> Any:
    migrate_configuration()
    with connect() as conn:
        row = conn.execute("SELECT value,secret FROM app_settings WHERE key=?", (key,)).fetchone()
    if not row:
        if default is None and key in SETTING_REGISTRY:
            return str(SETTING_REGISTRY[key]["default"])
        return default
    return _decrypt(str(row["value"])) if int(row["secret"]) else str(row["value"])

def set_setting(key: str, value: Any, *, secret: bool = False) -> None:
    assert_mutation_allowed(f"setting:{key}")
    migrate_configuration()
    if key in SETTING_REGISTRY:
        value = validate_registered_setting(key, value)
    text = "" if value is None else str(value)
    stored = _encrypt(text) if secret and text else text
    version = int(SETTING_REGISTRY.get(key, {}).get("version", CONFIG_SCHEMA_VERSION))
    with connect() as conn:
        previous = conn.execute("SELECT value,secret FROM app_settings WHERE key=?", (key,)).fetchone()
        old_value = None if not previous else ("[SECRET]" if int(previous["secret"]) else str(previous["value"]))
        new_value = "[SECRET]" if secret and text else text
        conn.execute(
            """INSERT INTO app_settings(key,value,secret,schema_version) VALUES(?,?,?,?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value,secret=excluded.secret,updated_at=CURRENT_TIMESTAMP,schema_version=excluded.schema_version""",
            (key, stored, 1 if secret else 0, version),
        )
        conn.execute("INSERT INTO app_settings_history(key,old_value,new_value,schema_version) VALUES(?,?,?,?)", (key, old_value, new_value, version))
        conn.commit()
    apply_runtime_setting(key, text)

def list_setting_history(key: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    ensure_schema()
    sql = "SELECT id,key,old_value,new_value,schema_version,changed_at FROM app_settings_history"
    params = []
    if key:
        sql += " WHERE key=?"
        params.append(key)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, min(1000, int(limit))))
    with connect() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]

def export_registered_settings() -> dict[str, Any]:
    return {
        key: get_setting(key, meta["default"])
        for key, meta in SETTING_REGISTRY.items()
        if not meta.get("secret")
    }

def import_registered_settings(values: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(values, dict):
        raise ValueError("Settings import must be an object.")
    unknown = sorted(set(values) - set(SETTING_REGISTRY))
    if unknown:
        raise ValueError("Unknown registered settings: " + ", ".join(unknown))
    validated = {
        key: validate_registered_setting(key, value)
        for key, value in values.items()
    }
    for key, value in validated.items():
        set_setting(key, value, secret=bool(SETTING_REGISTRY[key].get("secret")))
    return export_registered_settings()

def delete_setting(key: str) -> None:
    assert_mutation_allowed(f"setting-delete:{key}")
    ensure_schema()
    with connect() as conn:
        conn.execute("DELETE FROM app_settings WHERE key=?", (key,))
        conn.commit()

def get_bool(key: str, default: bool = False) -> bool:
    return str(get_setting(key, "true" if default else "false")).strip().lower() in {"1","true","yes","on"}

def get_int(key: str, default: int) -> int:
    try:
        return int(get_setting(key, str(default)))
    except (TypeError, ValueError):
        return default

def get_github_settings() -> dict[str, str]:
    return {
        "api_url": str(get_setting("github.api_url", "")),
        "repository": str(get_setting("github.repository", "")),
        "username": str(get_setting("github.username", "")),
        "token": str(get_setting("github.token", "", secret=True)),
    }
