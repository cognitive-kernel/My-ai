from __future__ import annotations

import hashlib
import json
import sqlite3
import logging

logger = logging.getLogger(__name__)
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .db import connect, settings

EXPORT_VERSION = "state-export-v1"
TABLES = ("chat_sessions","conversations","chat_attachments","session_state","session_events","stream_state","conversation_state")


def export_state(destination: str | Path) -> dict[str, Any]:
    path = Path(destination).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        data = {"format": EXPORT_VERSION, "created_at": datetime.now(timezone.utc).isoformat(), "tables": {}}
        for table in TABLES:
            try:
                rows = [dict(row) for row in conn.execute(f"SELECT * FROM {table}").fetchall()]
            except sqlite3.OperationalError:
                rows = []
            data["tables"][table] = rows
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    payload = {"format": EXPORT_VERSION, "sha256": hashlib.sha256(raw).hexdigest(), "data": data}
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return {"path":str(path),"format":EXPORT_VERSION,"sha256":payload["sha256"],"table_counts":{k:len(v) for k,v in data["tables"].items()}}


def verify_export(source: str | Path) -> dict[str, Any]:
    path=Path(source).expanduser().resolve()
    payload=json.loads(path.read_text(encoding="utf-8"))
    data=payload["data"]
    raw=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    actual=hashlib.sha256(raw).hexdigest()
    fmt=str(data.get("format") or "")
    return {"valid":actual==payload.get("sha256") and fmt.startswith("state-export-v"),"expected":payload.get("sha256"),"actual":actual,"format":fmt,"compatible":fmt==EXPORT_VERSION or fmt=="state-export-v0"}


def import_state(source: str | Path, *, allow_migration: bool = False) -> dict[str, Any]:
    verification=verify_export(source)
    if not verification["valid"]:
        raise ValueError("State export integrity verification failed.")
    payload=json.loads(Path(source).read_text(encoding="utf-8"))
    if payload["data"]["format"] != EXPORT_VERSION:
        if not allow_migration or payload["data"]["format"] != "state-export-v0":
            raise ValueError("Unsupported state export version.")
        payload["data"] = _migrate_v0(payload["data"])
    with connect() as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        for table in reversed(TABLES):
            try:
                conn.execute(f"DELETE FROM {table}")
            except sqlite3.OperationalError as exc:
                logger.info("STATE_RESTORE_TABLE_ABSENT table=%s error=%s", table, exc)
        for table in TABLES:
            rows=payload["data"]["tables"].get(table,[])
            if not rows: continue
            columns=list(rows[0].keys())
            placeholders=",".join("?" for _ in columns)
            conn.executemany(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})", [[row.get(c) for c in columns] for row in rows])
        conn.commit()
        counts = {}
        for table in TABLES:
            try:
                counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            except sqlite3.OperationalError:
                counts[table] = 0
        expected_counts = {table: len(payload["data"]["tables"].get(table, [])) for table in TABLES}
        if counts != expected_counts:
            raise RuntimeError(f"State restore integrity mismatch: expected={expected_counts} actual={counts}")
        conn.execute("PRAGMA foreign_keys=ON")
    return {"restored":True,"format":payload["data"]["format"],"sha256":verification["actual"],"table_counts":counts,"integrity_verified":True}


def database_snapshot(destination: str | Path) -> str:
    target=Path(destination).expanduser().resolve()
    target.parent.mkdir(parents=True,exist_ok=True)
    source=sqlite3.connect(Path(settings.db_path))
    dest=sqlite3.connect(target)
    try:
        source.backup(dest); dest.commit()
    finally:
        dest.close(); source.close()
    return str(target)


def _migrate_v0(data: dict[str, Any]) -> dict[str, Any]:
    tables = dict(data.get("tables") or {})
    tables.setdefault("session_state", [])
    tables.setdefault("session_events", [])
    tables.setdefault("stream_state", [])
    tables.setdefault("conversation_state", [])
    data = dict(data)
    data["format"] = EXPORT_VERSION
    data["migrated_from"] = "state-export-v0"
    data["tables"] = tables
    return data
