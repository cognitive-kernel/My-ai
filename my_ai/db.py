from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,kind TEXT NOT NULL DEFAULT 'chat',language TEXT,pinned INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS conversations (
 id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, role TEXT NOT NULL, content TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS knowledge (
 id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL, title TEXT NOT NULL,
 content TEXT NOT NULL, source_url TEXT, content_hash TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS learning_sessions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, language TEXT NOT NULL, topic TEXT NOT NULL,
 status TEXT NOT NULL, score REAL, notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS experiments (
 id INTEGER PRIMARY KEY AUTOINCREMENT, language TEXT NOT NULL, code TEXT NOT NULL,
 output TEXT, error TEXT, passed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS project_tasks (
 id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL, title TEXT NOT NULL,
 description TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
 title, content, topic, source_url, content='knowledge', content_rowid='id');
CREATE TABLE IF NOT EXISTS agent_runs (
 id INTEGER PRIMARY KEY AUTOINCREMENT, run_type TEXT NOT NULL, status TEXT NOT NULL,
 details TEXT, started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 finished_at TEXT);
CREATE TABLE IF NOT EXISTS generated_projects (
 id INTEGER PRIMARY KEY AUTOINCREMENT, language TEXT NOT NULL, request TEXT NOT NULL, code TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS help_updates (
 id INTEGER PRIMARY KEY AUTOINCREMENT, component TEXT NOT NULL, question TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending', answer TEXT NOT NULL, sources TEXT NOT NULL,
 proposed_update TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS security_scans (
 id INTEGER PRIMARY KEY AUTOINCREMENT, project_path TEXT NOT NULL, status TEXT NOT NULL,
 summary TEXT NOT NULL, findings TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
"""


def connect() -> sqlite3.Connection:
    path = Path(settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _knowledge_hash(topic: str, content: str) -> str:
    normalized = " ".join(str(content).split()).strip().casefold()
    # Content is the deduplication identity: identical knowledge is stored once
    # even when it was learned from different titles or sources.
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _deduplicate_knowledge(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT id,topic,content,source_url FROM knowledge ORDER BY id").fetchall()
    seen: dict[str, int] = {}
    for row in rows:
        digest = _knowledge_hash(row["topic"], row["content"])
        if digest in seen:
            keeper = seen[digest]
            # Preserve the best available provenance without creating another row.
            if not conn.execute("SELECT source_url FROM knowledge WHERE id=?", (keeper,)).fetchone()[0] and row["source_url"]:
                conn.execute("UPDATE knowledge SET source_url=? WHERE id=?", (row["source_url"], keeper))
            conn.execute("DELETE FROM knowledge WHERE id=?", (row["id"],))
        else:
            seen[digest] = int(row["id"])
            conn.execute("UPDATE knowledge SET content_hash=? WHERE id=?", (digest, row["id"]))


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        cols=[r[1] for r in conn.execute("PRAGMA table_info(conversations)").fetchall()]
        if "session_id" not in cols: conn.execute("ALTER TABLE conversations ADD COLUMN session_id INTEGER")
        cols_sessions=[r[1] for r in conn.execute("PRAGMA table_info(chat_sessions)").fetchall()]
        if "pinned" not in cols_sessions: conn.execute("ALTER TABLE chat_sessions ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
        cols_knowledge=[r[1] for r in conn.execute("PRAGMA table_info(knowledge)").fetchall()]
        if "content_hash" not in cols_knowledge: conn.execute("ALTER TABLE knowledge ADD COLUMN content_hash TEXT")
        if conn.execute("SELECT COUNT(*) FROM chat_sessions").fetchone()[0]==0:
            cur=conn.execute("INSERT INTO chat_sessions(title) VALUES(?)",("گفتگوی قبلی",))
            conn.execute("UPDATE conversations SET session_id=? WHERE session_id IS NULL",(cur.lastrowid,))
        _deduplicate_knowledge(conn)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_content_hash ON knowledge(content_hash)")
        conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
          INSERT INTO knowledge_fts(rowid,title,content,topic,source_url)
          VALUES(new.id,new.title,new.content,new.topic,new.source_url);
        END;
        CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
          INSERT INTO knowledge_fts(knowledge_fts,rowid,title,content,topic,source_url)
          VALUES('delete',old.id,old.title,old.content,old.topic,old.source_url);
        END;
        CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
          INSERT INTO knowledge_fts(knowledge_fts,rowid,title,content,topic,source_url)
          VALUES('delete',old.id,old.title,old.content,old.topic,old.source_url);
          INSERT INTO knowledge_fts(rowid,title,content,topic,source_url)
          VALUES(new.id,new.title,new.content,new.topic,new.source_url);
        END;
        """)
        # Rebuild FTS once so historical databases remain consistent after deduplication.
        conn.execute("INSERT INTO knowledge_fts(knowledge_fts) VALUES('rebuild')")


def execute(sql: str, params: tuple[Any, ...] = ()) -> int:
    with connect() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return int(cur.lastrowid or 0)


def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]


def remember_knowledge(topic: str, title: str, content: str, source_url: str | None = None) -> int:
    digest = _knowledge_hash(topic, content)
    with connect() as conn:
        row = conn.execute("SELECT id,source_url FROM knowledge WHERE content_hash=?", (digest,)).fetchone()
        if row:
            if not row["source_url"] and source_url:
                conn.execute("UPDATE knowledge SET source_url=? WHERE id=?", (source_url, row["id"]))
            conn.commit()
            return int(row["id"])
        cur = conn.execute(
            "INSERT INTO knowledge(topic,title,content,source_url,content_hash) VALUES(?,?,?,?,?)",
            (topic, title, content, source_url, digest),
        )
        conn.commit()
        return int(cur.lastrowid or 0)


def search_knowledge(query: str, limit: int = 8) -> list[dict[str, Any]]:
    tokens = [t for t in query.replace('"', " ").split() if t.isalnum()][:12]
    if not tokens:
        return []
    match = " ".join(f'"{t}"' for t in tokens)
    return fetch_all(
        """SELECT k.id,k.topic,k.title,k.content,k.source_url,k.created_at,
                  bm25(knowledge_fts) AS rank
           FROM knowledge_fts JOIN knowledge k ON k.id=knowledge_fts.rowid
           WHERE knowledge_fts MATCH ? ORDER BY rank LIMIT ?""",
        (match, limit),
    )
