from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status", "duration_ms", "user_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging() -> None:
    root = logging.getLogger()
    if not any(isinstance(h.formatter, JsonLogFormatter) for h in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonLogFormatter())
        root.addHandler(handler)

    # Persistent Settings UI value takes precedence over the environment variable.
    # Import lazily to avoid making logging configuration depend on DB initialization
    # during module import.
    try:
        from .settings_store import get_setting
        configured_level = str(get_setting("logging.level", "")).strip().upper()
    except (KeyError, TypeError, ValueError, OSError):
        configured_level = ""
    level_name = configured_level or os.getenv("MYAI_LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, level_name, logging.INFO)
    root.setLevel(log_level)
    destination = "console"
    try:
        destination = str(get_setting("observability.log_destination", "console") or "console").strip()
    except (KeyError, TypeError, ValueError, OSError):
        destination = "console"
    if destination.startswith("file:"):
        raw_path = Path(destination[5:].strip()).expanduser()
        log_root = Path("data/logs").resolve()
        target = raw_path.resolve() if raw_path.is_absolute() else (Path.cwd() / raw_path).resolve()
        try:
            target.relative_to(log_root)
        except ValueError:
            target = log_root / "my-ai.log"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not any(isinstance(h, logging.FileHandler) and Path(getattr(h, "baseFilename", "")).resolve() == target for h in root.handlers):
            file_handler = logging.FileHandler(target, encoding="utf-8")
            file_handler.setFormatter(JsonLogFormatter())
            root.addHandler(file_handler)

    # Keep application logger filtering explicit because Uvicorn may reconfigure
    # the root logger after application import.
    logging.getLogger("my_ai").setLevel(log_level)

    # Routine HTTP polling/access lines are intentionally quiet; warnings/errors remain visible.
    logging.getLogger("my_ai.http").setLevel(
        getattr(logging, os.getenv("MYAI_HTTP_LOG_LEVEL", "WARNING").upper(), logging.WARNING)
    )
    logging.getLogger("uvicorn.access").setLevel(
        getattr(logging, os.getenv("MYAI_UVICORN_ACCESS_LOG_LEVEL", "WARNING").upper(), logging.WARNING)
    )
    http_client_level = getattr(
        logging,
        os.getenv("MYAI_HTTP_CLIENT_LOG_LEVEL", "WARNING").upper(),
        logging.WARNING,
    )
    logging.getLogger("httpx").setLevel(http_client_level)
    logging.getLogger("httpcore").setLevel(http_client_level)


def request_log(*, request_id: str, method: str, path: str, status: int, duration_ms: float, user_id: int | None = None) -> dict[str, Any]:
    return {"request_id": request_id, "method": method, "path": path, "status": status, "duration_ms": round(duration_ms, 3), "user_id": user_id}
