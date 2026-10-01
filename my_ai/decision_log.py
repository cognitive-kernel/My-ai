from __future__ import annotations

import json
from .config import settings
from .db import execute

def record(event: str, decision: str, details: dict[str, object] | None = None) -> None:
    if not settings.decision_log:
        return
    try:
        execute(
            "INSERT INTO decision_log(event,decision,details) VALUES(?,?,?)",
            (event, decision, json.dumps(details or {}, ensure_ascii=False)),
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("DECISION_LOG_PERSIST_FAILED: %s", exc)
