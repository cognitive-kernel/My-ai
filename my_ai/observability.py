from __future__ import annotations

import json
import logging
import logging.handlers
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
    level = getattr(logging, os.getenv("MYAI_LOG_LEVEL", "INFO").upper(), logging.INFO)
    root.setLevel(level)

    formatter = JsonLogFormatter()

    if not any(getattr(handler, "_myai_console", False) for handler in root.handlers):
        console = logging.StreamHandler()
        console.setLevel(logging.ERROR)
        console.setFormatter(formatter)
        console._myai_console = True
        root.addHandler(console)

    log_dir = Path(os.getenv("MYAI_LOG_DIR", "logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "my_ai.log"

    if not any(getattr(handler, "_myai_file", False) for handler in root.handlers):
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler._myai_file = True
        root.addHandler(file_handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def request_log(*, request_id: str, method: str, path: str, status: int, duration_ms: float, user_id: int | None = None) -> dict[str, Any]:
    return {"request_id": request_id, "method": method, "path": path, "status": status, "duration_ms": round(duration_ms, 3), "user_id": user_id}
