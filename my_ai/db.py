from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
 id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL, content TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS knowledge (
 id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL, title TEXT NOT NULL,
 content TEXT NOT NULL, source_url TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
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
"""

def connect() -> sqlite3.Connection:
    path = Path(settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        # Keep FTS synchronized for rows created by this application.
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

def execute(sql: str, params: tuple[Any, ...] = ()) -> int:
    with connect() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return int(cur.lastrowid or 0)

def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]

def search_knowledge(query: str, limit: int = 8) -> list[dict[str, Any]]:
    # FTS5 MATCH syntax is intentionally restricted to tokens to avoid operators
    # being supplied by an API caller.
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
