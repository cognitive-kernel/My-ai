"""Schema-driven graphical forms for every control-plane module.

The GUI intentionally uses the same control-plane persistence as the CLI.  A module
form is a typed front-end schema; arbitrary JSON remains available for forward
compatibility, but normal users do not need to write JSON.
"""
from __future__ import annotations

from typing import Any

from .control_plane import namespace_catalog


COMMON_FIELDS = (
    {"name": "description", "label": "توضیح", "type": "text", "default": ""},
    {"name": "version", "label": "نسخه", "type": "text", "default": "1"},
)

GROUP_FIELDS: dict[str, tuple[dict[str, Any], ...]] = {
    "agent": (
        {"name": "strategy", "label": "Strategy", "type": "select", "choices": ["adaptive", "reactive", "plan-execute", "graph"], "default": "adaptive"},
        {"name": "timeout_seconds", "label": "Timeout (ثانیه)", "type": "number", "min": 1, "max": 86400, "default": 300},
        {"name": "max_steps", "label": "حداکثر گام", "type": "number", "min": 1, "max": 1000, "default": 20},
        {"name": "enabled", "label": "فعال", "type": "boolean", "default": True},
        {"name": "policy", "label": "Policy", "type": "json", "default": "{}"},
    ),
    "tools": (
        {"name": "description", "label": "توضیح ابزار", "type": "text", "default": ""},
        {"name": "timeout", "label": "Timeout (ثانیه)", "type": "number", "min": 0.1, "max": 3600, "default": 30},
        {"name": "retries", "label": "تعداد Retry", "type": "number", "min": 0, "max": 20, "default": 2},
        {"name": "permissions", "label": "مجوزها", "type": "text", "default": ""},
        {"name": "tasks", "label": "Taskها", "type": "text", "default": ""},
        {"name": "input_schema", "label": "Input Schema", "type": "json", "default": "{}"},
        {"name": "output_schema", "label": "Output Schema", "type": "json", "default": "{}"},
    ),
    "memory": (
        {"name": "backend", "label": "Backend", "type": "select", "choices": ["sqlite", "file", "hybrid"], "default": "sqlite"},
        {"name": "retention_days", "label": "Retention (روز)", "type": "number", "min": 1, "max": 36500, "default": 365},
        {"name": "provenance", "label": "Provenance", "type": "boolean", "default": True},
        {"name": "confidence", "label": "Confidence", "type": "number", "min": 0, "max": 1, "default": 0.5},
        {"name": "policy", "label": "Lifecycle Policy", "type": "json", "default": "{}"},
    ),
    "research": (
        {"name": "provider", "label": "Provider", "type": "text", "default": "duckduckgo-html"},
        {"name": "timeout_seconds", "label": "Timeout (ثانیه)", "type": "number", "min": 1, "max": 600, "default": 15},
        {"name": "allowlist", "label": "Domain Allowlist", "type": "text", "default": ""},
        {"name": "denylist", "label": "Domain Denylist", "type": "text", "default": ""},
        {"name": "freshness_days", "label": "تازگی منبع (روز)", "type": "number", "min": 0, "max": 36500, "default": 30},
        {"name": "require_approval", "label": "نیازمند تأیید", "type": "boolean", "default": False},
    ),
    "security": (
        {"name": "mode", "label": "Policy Mode", "type": "select", "choices": ["deny", "approval", "sandbox", "allow"], "default": "deny"},
        {"name": "require_approval", "label": "تأیید عملیات حساس", "type": "boolean", "default": True},
        {"name": "rules", "label": "Rules", "type": "json", "default": "{}"},
        {"name": "audit", "label": "Audit", "type": "boolean", "default": True},
    ),
    "scheduler": (
        {"name": "schedule", "label": "Schedule", "type": "text", "default": "hourly"},
        {"name": "interval_seconds", "label": "Interval (ثانیه)", "type": "number", "min": 60, "max": 86400, "default": 3600},
        {"name": "workers", "label": "Workers", "type": "number", "min": 1, "max": 128, "default": 2},
        {"name": "concurrency", "label": "Concurrency", "type": "number", "min": 1, "max": 128, "default": 2},
        {"name": "priority", "label": "Priority", "type": "number", "min": 0, "max": 100000, "default": 100},
        {"name": "enabled", "label": "فعال", "type": "boolean", "default": True},
    ),
    "execution": (
        {"name": "mode", "label": "Execution Mode", "type": "select", "choices": ["local", "sandbox", "container"], "default": "local"},
        {"name": "timeout_seconds", "label": "Timeout (ثانیه)", "type": "number", "min": 1, "max": 86400, "default": 10},
        {"name": "memory_mb", "label": "Memory (MB)", "type": "number", "min": 64, "max": 1048576, "default": 2048},
        {"name": "cpu_cores", "label": "CPU Cores", "type": "number", "min": 0.1, "max": 128, "default": 1},
        {"name": "sandbox", "label": "Sandbox", "type": "boolean", "default": True},
    ),
    "integrations": (
        {"name": "provider", "label": "Provider", "type": "text", "default": ""},
        {"name": "endpoint", "label": "Endpoint", "type": "text", "default": ""},
        {"name": "events", "label": "Events", "type": "text", "default": ""},
        {"name": "credentials", "label": "Credentials", "type": "json", "default": "{}"},
        {"name": "enabled", "label": "فعال", "type": "boolean", "default": True},
    ),
    "server": (
        {"name": "host", "label": "Host", "type": "text", "default": "127.0.0.1"},
        {"name": "port", "label": "Port", "type": "number", "min": 1, "max": 65535, "default": 8000},
        {"name": "timeout_seconds", "label": "Request Timeout", "type": "number", "min": 1, "max": 3600, "default": 60},
        {"name": "rate_limit_per_minute", "label": "Rate Limit", "type": "number", "min": 1, "max": 100000, "default": 120},
        {"name": "maintenance", "label": "Maintenance", "type": "boolean", "default": False},
    ),
    "observability": (
        {"name": "enabled", "label": "فعال", "type": "boolean", "default": True},
        {"name": "destination", "label": "Log Destination", "type": "text", "default": "console"},
        {"name": "retention_days", "label": "Retention (روز)", "type": "number", "min": 1, "max": 3650, "default": 30},
        {"name": "rules", "label": "Alert Rules", "type": "json", "default": "[]"},
        {"name": "dashboard", "label": "Dashboard", "type": "json", "default": "{}"},
    ),
    "database": (
        {"name": "path", "label": "Database Path", "type": "text", "default": "data/my_ai.db"},
        {"name": "schedule", "label": "Backup Schedule", "type": "text", "default": "manual"},
        {"name": "retention", "label": "Retention", "type": "number", "min": 1, "max": 3650, "default": 7},
        {"name": "encryption", "label": "Encryption", "type": "select", "choices": ["none", "aes-gcm"], "default": "none"},
        {"name": "destination", "label": "Backup Destination", "type": "text", "default": "data/backups"},
    ),
    "multimodal": (
        {"name": "provider", "label": "Provider", "type": "text", "default": "local"},
        {"name": "model", "label": "Model", "type": "text", "default": ""},
        {"name": "routing", "label": "Routing", "type": "select", "choices": ["automatic", "local", "disabled"], "default": "automatic"},
        {"name": "enabled", "label": "فعال", "type": "boolean", "default": True},
    ),
    "evaluation": (
        {"name": "enabled", "label": "فعال", "type": "boolean", "default": True},
        {"name": "baseline", "label": "Baseline", "type": "text", "default": ""},
        {"name": "benchmark", "label": "Benchmark", "type": "json", "default": "{}"},
        {"name": "threshold", "label": "Minimum Score", "type": "number", "min": 0, "max": 1, "default": 0.8},
    ),
    "experience": (
        {"name": "version", "label": "Environment Version", "type": "text", "default": ""},
        {"name": "provenance", "label": "Provenance", "type": "json", "default": "{}"},
        {"name": "evidence", "label": "Evidence", "type": "json", "default": "[]"},
        {"name": "compatibility", "label": "Compatibility", "type": "text", "default": ""},
        {"name": "status", "label": "Status", "type": "select", "choices": ["candidate", "verified", "invalid", "deprecated"], "default": "candidate"},
    ),
}

PREFIX_ALIASES = {
    "agent": "agent",
    "tools": "tools",
    "memory": "memory",
    "research": "research",
    "security": "security",
    "scheduler": "scheduler",
    "execution": "execution",
    "integrations": "integrations",
    "server": "server",
    "observability": "observability",
    "database": "database",
    "multimodal": "multimodal",
    "evaluation": "evaluation",
    "experience": "experience",
}

def _group(namespace: str) -> str:
    return PREFIX_ALIASES.get(namespace.split(".", 1)[0], "agent" if namespace.startswith("agent.") else "agent")


def module_form_schema(namespace: str) -> dict[str, Any]:
    """Return a stable graphical form schema for a control-plane namespace."""
    group = _group(namespace)
    fields = list(COMMON_FIELDS) + list(GROUP_FIELDS[group])
    seen: set[str] = set()
    unique = []
    for field in fields:
        if field["name"] in seen:
            continue
        seen.add(field["name"])
        unique.append(dict(field))
    return {"namespace": namespace, "group": group, "fields": unique, "timeout_seconds": 30}


def module_form_catalog() -> list[dict[str, Any]]:
    return [module_form_schema(namespace) for namespace in namespace_catalog()]
