from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,kind TEXT NOT NULL DEFAULT 'chat',language TEXT,pinned INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS knowledge (id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL, source_url TEXT, content_hash TEXT, verification_status TEXT NOT NULL DEFAULT 'unverified', verified_at TEXT, verified_by INTEGER, confidence REAL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS knowledge_embeddings (knowledge_id INTEGER NOT NULL, content_hash TEXT NOT NULL, model TEXT NOT NULL, embedding TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(knowledge_id,model), FOREIGN KEY(knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS learning_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, language TEXT NOT NULL, topic TEXT NOT NULL, status TEXT NOT NULL, score REAL, notes TEXT, progress_percent REAL NOT NULL DEFAULT 0, phase TEXT NOT NULL DEFAULT 'starting', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS experiments (id INTEGER PRIMARY KEY AUTOINCREMENT, language TEXT NOT NULL, code TEXT NOT NULL, output TEXT, error TEXT, passed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS project_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(title, content, topic, source_url, content='knowledge', content_rowid='id');
CREATE TABLE IF NOT EXISTS agent_runs (id INTEGER PRIMARY KEY AUTOINCREMENT, run_type TEXT NOT NULL, status TEXT NOT NULL, details TEXT, started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, finished_at TEXT);
CREATE TABLE IF NOT EXISTS generated_projects (id INTEGER PRIMARY KEY AUTOINCREMENT, language TEXT NOT NULL, request TEXT NOT NULL, code TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS help_updates (id INTEGER PRIMARY KEY AUTOINCREMENT, component TEXT NOT NULL, question TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', answer TEXT NOT NULL, sources TEXT NOT NULL, proposed_update TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS security_scans (id INTEGER PRIMARY KEY AUTOINCREMENT, project_path TEXT NOT NULL, status TEXT NOT NULL, summary TEXT NOT NULL, findings TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS fix_attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, patch TEXT, test_result TEXT, activated INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 username TEXT NOT NULL UNIQUE,
 password_salt TEXT NOT NULL,
 password_hash TEXT NOT NULL,
 display_name TEXT NOT NULL DEFAULT '',
 role TEXT NOT NULL DEFAULT 'user',
 active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS auth_sessions (
 token TEXT PRIMARY KEY,
 user_id INTEGER NOT NULL,
 expires_at TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS tool_permissions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL,
 tool_name TEXT NOT NULL,
 action TEXT NOT NULL,
 allowed INTEGER NOT NULL DEFAULT 0,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE(user_id,tool_name,action),
 FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS audit_log (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER,
 username TEXT NOT NULL,
 tool_name TEXT NOT NULL,
 action TEXT NOT NULL,
 status TEXT NOT NULL,
 details TEXT,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_log(created_at);
CREATE TABLE IF NOT EXISTS skills (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 version TEXT NOT NULL,
 score REAL NOT NULL DEFAULT 0,
 verified INTEGER NOT NULL DEFAULT 0,
 last_verified TEXT,
 UNIQUE(name,version)
);
CREATE TABLE IF NOT EXISTS skill_evidence (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 skill_id INTEGER NOT NULL,
 kind TEXT NOT NULL,
 passed INTEGER NOT NULL DEFAULT 0,
 evidence TEXT NOT NULL,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(skill_id) REFERENCES skills(id) ON DELETE CASCADE
);
"""

def connect() -> sqlite3.Connection:
    path = Path(settings.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.create_function("normalize_search", 1, _normalize_search_text)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn

def _normalize_search_text(value: str) -> str:
    return " ".join(str(value).replace("ي","ی").replace("ى","ی").replace("ك","ک").replace("\u200c"," ").replace("\u200d"," ").replace("\u0640","").split()).casefold()

def _knowledge_hash(topic: str, content: str) -> str:
    normalized = _normalize_search_text(f"{topic}\n{content}")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def _deduplicate_knowledge(conn: sqlite3.Connection) -> None:
    rows = conn.execute("SELECT id,topic,content,source_url FROM knowledge ORDER BY id").fetchall()
    seen: dict[str, int] = {}
    for row in rows:
        digest = _knowledge_hash(row["topic"], row["content"])
        if digest in seen:
            keeper = seen[digest]
            if not conn.execute("SELECT source_url FROM knowledge WHERE id=?", (keeper,)).fetchone()[0] and row["source_url"]:
                conn.execute("UPDATE knowledge SET source_url=? WHERE id=?", (row["source_url"], keeper))
            conn.execute("DELETE FROM knowledge WHERE id=?", (row["id"],))
        else:
            seen[digest] = int(row["id"])
            conn.execute("UPDATE knowledge SET content_hash=? WHERE id=?", (digest, row["id"]))

def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.executescript("""
        DROP TRIGGER IF EXISTS knowledge_ai;
        DROP TRIGGER IF EXISTS knowledge_ad;
        DROP TRIGGER IF EXISTS knowledge_au;
        """)
        cols=[r[1] for r in conn.execute("PRAGMA table_info(conversations)").fetchall()]
        if "session_id" not in cols: conn.execute("ALTER TABLE conversations ADD COLUMN session_id INTEGER")
        cols_sessions=[r[1] for r in conn.execute("PRAGMA table_info(chat_sessions)").fetchall()]
        if "pinned" not in cols_sessions: conn.execute("ALTER TABLE chat_sessions ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
        if "user_id" not in cols_sessions: conn.execute("ALTER TABLE chat_sessions ADD COLUMN user_id INTEGER")
        cols_learning=[r[1] for r in conn.execute("PRAGMA table_info(learning_sessions)").fetchall()]
        if "progress_percent" not in cols_learning: conn.execute("ALTER TABLE learning_sessions ADD COLUMN progress_percent REAL NOT NULL DEFAULT 0")
        if "phase" not in cols_learning: conn.execute("ALTER TABLE learning_sessions ADD COLUMN phase TEXT NOT NULL DEFAULT 'starting'")
        cols_knowledge=[r[1] for r in conn.execute("PRAGMA table_info(knowledge)").fetchall()]
        if "content_hash" not in cols_knowledge: conn.execute("ALTER TABLE knowledge ADD COLUMN content_hash TEXT")
        if "verification_status" not in cols_knowledge: conn.execute("ALTER TABLE knowledge ADD COLUMN verification_status TEXT NOT NULL DEFAULT 'unverified'")
        if "verified_at" not in cols_knowledge: conn.execute("ALTER TABLE knowledge ADD COLUMN verified_at TEXT")
        if "verified_by" not in cols_knowledge: conn.execute("ALTER TABLE knowledge ADD COLUMN verified_by INTEGER")
        if "confidence" not in cols_knowledge: conn.execute("ALTER TABLE knowledge ADD COLUMN confidence REAL")
        admin_row = conn.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
        if conn.execute("SELECT COUNT(*) FROM chat_sessions").fetchone()[0]==0 and conn.execute("SELECT COUNT(*) FROM conversations WHERE session_id IS NULL").fetchone()[0]:
            cur=conn.execute("INSERT INTO chat_sessions(title,user_id) VALUES(?,?)",("گفتگوی قبلی", admin_row[0] if admin_row else None))
            conn.execute("UPDATE conversations SET session_id=? WHERE session_id IS NULL",(cur.lastrowid,))
        elif admin_row:
            conn.execute("UPDATE chat_sessions SET user_id=? WHERE user_id IS NULL",(admin_row[0],))
        if admin_row:
            conn.execute("UPDATE conversations SET session_id=(SELECT id FROM chat_sessions WHERE user_id=? ORDER BY id LIMIT 1) WHERE session_id IS NULL",(admin_row[0],))
        _deduplicate_knowledge(conn)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_content_hash ON knowledge(content_hash)")
        conn.executescript("""
        CREATE TRIGGER knowledge_ai AFTER INSERT ON knowledge BEGIN
          INSERT INTO knowledge_fts(rowid,title,content,topic,source_url) VALUES(new.id,normalize_search(new.title),normalize_search(new.content),normalize_search(new.topic),normalize_search(new.source_url));
        END;
        CREATE TRIGGER knowledge_ad AFTER DELETE ON knowledge BEGIN
          INSERT INTO knowledge_fts(knowledge_fts,rowid,title,content,topic,source_url) VALUES('delete',old.id,normalize_search(old.title),normalize_search(old.content),normalize_search(old.topic),normalize_search(old.source_url));
        END;
        CREATE TRIGGER knowledge_au AFTER UPDATE ON knowledge BEGIN
          INSERT INTO knowledge_fts(knowledge_fts,rowid,title,content,topic,source_url) VALUES('delete',old.id,old.title,old.content,old.topic,old.source_url);
          INSERT INTO knowledge_fts(rowid,title,content,topic,source_url) VALUES(new.id,normalize_search(new.title),normalize_search(new.content),normalize_search(new.topic),normalize_search(new.source_url));
        END;
        """)
        conn.execute("INSERT INTO knowledge_fts(knowledge_fts) VALUES('delete-all')")
        for row in conn.execute("SELECT id,title,content,topic,source_url FROM knowledge").fetchall():
            conn.execute(
                "INSERT INTO knowledge_fts(rowid,title,content,topic,source_url) VALUES(?,?,?,?,?)",
                (row["id"], _normalize_search_text(row["title"]), _normalize_search_text(row["content"]), _normalize_search_text(row["topic"]), _normalize_search_text(row["source_url"] or "")),
            )

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
        cur = conn.execute("INSERT INTO knowledge(topic,title,content,source_url,content_hash) VALUES(?,?,?,?,?)",(topic,title,content,source_url,digest))
        conn.commit()
        return int(cur.lastrowid or 0)

def search_knowledge(query: str, limit: int = 8) -> list[dict[str, Any]]:
    normalized_query = _normalize_search_text(query)
    tokens = [t for t in normalized_query.replace('"', " ").split() if t][:12]
    if not tokens: return []
    match = " ".join(f'"{t}"' for t in tokens)
    return fetch_all(
        """SELECT k.id,k.topic,k.title,k.content,k.source_url,k.verification_status,k.confidence,k.created_at,
                  bm25(knowledge_fts) AS rank
           FROM knowledge_fts JOIN knowledge k ON k.id=knowledge_fts.rowid
           WHERE knowledge_fts MATCH ? ORDER BY rank LIMIT ?""",
        (match, limit),
    )
