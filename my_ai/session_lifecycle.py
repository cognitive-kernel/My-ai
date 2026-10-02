from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from .db import connect, execute, fetch_all

SESSION_TTL_SECONDS = 24 * 60 * 60
STREAM_TTL_SECONDS = 15 * 60


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_schema() -> None:
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS session_state (
            session_id INTEGER PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'active',
            version INTEGER NOT NULL DEFAULT 1,
            expires_at TEXT,
            last_sequence INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS session_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            sequence INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            checksum TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(session_id, sequence),
            FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS stream_state (
            stream_id TEXT PRIMARY KEY,
            session_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            next_sequence INTEGER NOT NULL DEFAULT 1,
            context_hash TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
        );
        """)


def create_session(user_id: int | None = None, title: str = "گفتگوی جدید", language: str | None = None) -> int:
    ensure_schema()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO chat_sessions(title,user_id,language) VALUES(?,?,?)",
            (title[:200], user_id, language),
        )
        session_id = int(cur.lastrowid)
        expires = (datetime.now(timezone.utc) + timedelta(seconds=SESSION_TTL_SECONDS)).isoformat()
        conn.execute(
            "INSERT INTO session_state(session_id,status,expires_at) VALUES(?,?,?)",
            (session_id, "active", expires),
        )
        conn.commit()
        return session_id


def recover_session(session_id: int, user_id: int | None = None) -> dict[str, Any]:
    ensure_schema()
    rows = fetch_all(
        """SELECT s.id,s.title,s.kind,s.language,s.pinned,s.created_at,s.updated_at,
                  COALESCE(st.status,'active') status,st.version,st.expires_at,
                  COALESCE(st.last_sequence,0) last_sequence
           FROM chat_sessions s LEFT JOIN session_state st ON st.session_id=s.id
           WHERE s.id=? AND (? IS NULL OR s.user_id=?)""",
        (session_id, user_id, user_id),
    )
    if not rows:
        raise ValueError("Session not found.")
    state = rows[0]
    if state["status"] == "expired":
        return state
    if state["expires_at"] and datetime.fromisoformat(str(state["expires_at"]).replace("Z","+00:00")) <= datetime.now(timezone.utc):
        execute("UPDATE session_state SET status='expired',updated_at=CURRENT_TIMESTAMP WHERE session_id=?", (session_id,))
        state["status"] = "expired"
    state["messages"] = fetch_all(
        "SELECT id,role,content,created_at FROM conversations WHERE session_id=? ORDER BY id",
        (session_id,),
    )
    state["attachments"] = fetch_all(
        "SELECT id,conversation_id,name,path,size,mime_type,created_at FROM chat_attachments WHERE session_id=? ORDER BY id",
        (session_id,),
    )
    return state


def append_event(session_id: int, event_type: str, payload: dict[str, Any], user_id: int | None = None) -> dict[str, Any]:
    ensure_schema()
    with connect() as conn:
        row = conn.execute("SELECT st.status,st.last_sequence FROM session_state st JOIN chat_sessions s ON s.id=st.session_id WHERE st.session_id=? AND (? IS NULL OR s.user_id=?)", (session_id,user_id,user_id)).fetchone()
        if not row:
            raise ValueError("Session state not found.")
        if row["status"] not in {"active", "recovering"}:
            raise ValueError(f"Session is not writable: {row['status']}")
        seq = int(row["last_sequence"]) + 1
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        checksum = hashlib.sha256(f"{session_id}:{seq}:{event_type}:{body}".encode()).hexdigest()
        conn.execute(
            "INSERT INTO session_events(session_id,sequence,event_type,payload,checksum) VALUES(?,?,?,?,?)",
            (session_id, seq, event_type, body, checksum),
        )
        conn.execute(
            "UPDATE session_state SET last_sequence=?,updated_at=CURRENT_TIMESTAMP WHERE session_id=?",
            (seq, session_id),
        )
        conn.execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
        conn.commit()
    return {"session_id": session_id, "sequence": seq, "checksum": checksum}


def open_stream(session_id: int, context: str = "") -> dict[str, Any]:
    ensure_schema()
    state = recover_session(session_id)
    if state["status"] == "expired":
        raise ValueError("Session expired.")
    stream_id = uuid.uuid4().hex
    context_hash = hashlib.sha256(context.encode("utf-8")).hexdigest()
    execute(
        "INSERT INTO stream_state(stream_id,session_id,status,next_sequence,context_hash) VALUES(?,?,?,1,?)",
        (stream_id, session_id, "open", context_hash),
    )
    return {"stream_id": stream_id, "session_id": session_id, "next_sequence": 1, "context_hash": context_hash}


def stream_chunk(stream_id: str, chunk: str, sequence: int | None = None) -> dict[str, Any]:
    rows = fetch_all("SELECT * FROM stream_state WHERE stream_id=?", (stream_id,))
    if not rows:
        raise ValueError("Stream not found.")
    state = rows[0]
    if state["status"] != "open":
        raise ValueError("Stream is not open.")
    expected = int(state["next_sequence"])
    sequence = expected if sequence is None else int(sequence)
    if sequence != expected:
        raise ValueError(f"Stream sequence mismatch: expected {expected}, got {sequence}.")
    payload = {"stream_id": stream_id, "sequence": sequence, "chunk": str(chunk)}
    append_event(int(state["session_id"]), "stream.chunk", payload)
    checksum = hashlib.sha256(json.dumps(payload,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    execute("UPDATE stream_state SET next_sequence=?,updated_at=CURRENT_TIMESTAMP WHERE stream_id=?", (sequence + 1, stream_id))
    return {**payload, "checksum": checksum}


def close_stream(stream_id: str, status: str = "completed") -> dict[str, Any]:
    if status not in {"completed", "interrupted", "failed", "reconnected"}:
        raise ValueError("Invalid stream terminal state.")
    rows = fetch_all("SELECT * FROM stream_state WHERE stream_id=?", (stream_id,))
    if not rows:
        raise ValueError("Stream not found.")
    execute("UPDATE stream_state SET status=?,updated_at=CURRENT_TIMESTAMP WHERE stream_id=?", (status, stream_id))
    append_event(int(rows[0]["session_id"]), "stream.closed", {"stream_id": stream_id, "status": status})
    return {"stream_id": stream_id, "status": status}


def reconnect_stream(stream_id: str) -> dict[str, Any]:
    rows = fetch_all("SELECT * FROM stream_state WHERE stream_id=?", (stream_id,))
    if not rows:
        raise ValueError("Stream not found.")
    state = rows[0]
    execute("UPDATE stream_state SET status='open',updated_at=CURRENT_TIMESTAMP WHERE stream_id=?", (stream_id,))
    return {
        "stream_id": stream_id,
        "session_id": state["session_id"],
        "next_sequence": state["next_sequence"],
        "context_hash": state["context_hash"],
        "status": "open",
    }


def verify_integrity(session_id: int) -> dict[str, Any]:
    ensure_schema()
    rows = fetch_all("SELECT sequence,event_type,payload,checksum FROM session_events WHERE session_id=? ORDER BY sequence", (session_id,))
    expected = 1
    valid = True
    for row in rows:
        body = str(row["payload"])
        checksum = hashlib.sha256(f"{session_id}:{row['sequence']}:{row['event_type']}:{body}".encode()).hexdigest()
        if int(row["sequence"]) != expected or checksum != row["checksum"]:
            valid = False
            break
        expected += 1
    return {"session_id": session_id, "valid": valid, "event_count": len(rows), "last_sequence": expected - 1}


def expire_sessions() -> int:
    ensure_schema()
    return execute(
        "UPDATE session_state SET status='expired',updated_at=CURRENT_TIMESTAMP WHERE status='active' AND expires_at IS NOT NULL AND expires_at<=?",
        (_now(),),
    )
