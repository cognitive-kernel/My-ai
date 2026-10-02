from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from .db import execute, fetch_all

def ensure_schema():
    execute("CREATE TABLE IF NOT EXISTS scheduler_events (id INTEGER PRIMARY KEY AUTOINCREMENT, language TEXT NOT NULL, event TEXT NOT NULL, details TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    execute("CREATE INDEX IF NOT EXISTS idx_scheduler_events_language ON scheduler_events(language,created_at)")

def record(language: str, event: str, **details):
    ensure_schema()
    execute("INSERT INTO scheduler_events(language,event,details) VALUES(?,?,?)",(str(language),str(event),json.dumps(details,ensure_ascii=False,default=str)))

def snapshot():
    ensure_schema()
    rows=fetch_all("SELECT language,event,details,created_at FROM scheduler_events ORDER BY id DESC LIMIT 200")
    return [{"language":r["language"],"event":r["event"],"details":json.loads(r["details"] or "{}"),"created_at":r["created_at"]} for r in rows]

def mark_stale(max_age_seconds: float = 120.0) -> int:
    ensure_schema()
    cutoff=datetime.now(timezone.utc).timestamp()-float(max_age_seconds)
    rows=fetch_all("SELECT language,updated_at,status FROM learning_workers WHERE status IN ('running','retrying')")
    count=0
    for row in rows:
        try:
            stamp=datetime.fromisoformat(str(row["updated_at"]).replace("Z","+00:00")).timestamp()
        except ValueError:
            continue
        if stamp < cutoff:
            record(row["language"],"stale_worker",status=row["status"],age_seconds=round(time.time()-stamp,1))
            execute("UPDATE learning_workers SET status='retrying',stage='retrying',error=? WHERE lower(language)=lower(?)",("worker heartbeat stale",row["language"]))
            count += 1
    return count
