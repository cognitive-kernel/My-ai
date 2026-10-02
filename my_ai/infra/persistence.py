from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from .config import settings


def _write_blocked() -> bool:
    import os
    return os.getenv("MYAI_READ_ONLY", "false").strip().lower() == "true"


SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,kind TEXT NOT NULL DEFAULT 'chat',language TEXT,pinned INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS chat_attachments (id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER, session_id INTEGER NOT NULL, name TEXT NOT NULL, path TEXT NOT NULL, size INTEGER NOT NULL DEFAULT 0, mime_type TEXT NOT NULL DEFAULT 'application/octet-stream', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE, FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS knowledge (id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL, source_url TEXT, content_hash TEXT, verification_status TEXT NOT NULL DEFAULT 'unverified', verified_at TEXT, verified_by INTEGER, confidence REAL, product TEXT, version TEXT, validity_status TEXT NOT NULL DEFAULT 'unknown', replaced_by_version TEXT, compatibility TEXT NOT NULL DEFAULT 'unknown', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS knowledge_embeddings (knowledge_id INTEGER NOT NULL, content_hash TEXT NOT NULL, model TEXT NOT NULL, embedding TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(knowledge_id,model), FOREIGN KEY(knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS learning_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, language TEXT NOT NULL, topic TEXT NOT NULL, status TEXT NOT NULL, score REAL, notes TEXT, progress_percent REAL NOT NULL DEFAULT 0, phase TEXT NOT NULL DEFAULT 'starting', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS learning_runtime (id INTEGER PRIMARY KEY CHECK(id=1), language TEXT, session_id INTEGER, status TEXT NOT NULL DEFAULT 'idle', started_at TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(session_id) REFERENCES learning_sessions(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS learning_workers (id INTEGER PRIMARY KEY AUTOINCREMENT, language TEXT NOT NULL UNIQUE, session_id INTEGER, status TEXT NOT NULL DEFAULT 'idle', stage TEXT NOT NULL DEFAULT 'idle', current_topic TEXT, error TEXT, last_result TEXT, started_at TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(session_id) REFERENCES learning_sessions(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS learning_experiences (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER, language TEXT NOT NULL, topic TEXT NOT NULL, kind TEXT NOT NULL, action TEXT NOT NULL DEFAULT '', content TEXT NOT NULL, error TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(session_id) REFERENCES learning_sessions(id) ON DELETE SET NULL);
CREATE INDEX IF NOT EXISTS idx_learning_experiences_topic ON learning_experiences(language,topic,created_at);
CREATE TABLE IF NOT EXISTS learning_worker_leases (language TEXT PRIMARY KEY, owner TEXT NOT NULL, lease_until REAL NOT NULL);
CREATE TABLE IF NOT EXISTS experiments (id INTEGER PRIMARY KEY AUTOINCREMENT, language TEXT NOT NULL, code TEXT NOT NULL, output TEXT, error TEXT, passed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS project_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, project TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(title, content, topic, source_url, content='knowledge', content_rowid='id');
CREATE TABLE IF NOT EXISTS agent_runs (id INTEGER PRIMARY KEY AUTOINCREMENT, run_type TEXT NOT NULL, status TEXT NOT NULL, details TEXT, started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, finished_at TEXT);
CREATE TABLE IF NOT EXISTS generated_projects (id INTEGER PRIMARY KEY AUTOINCREMENT, language TEXT NOT NULL, request TEXT NOT NULL, code TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS help_updates (id INTEGER PRIMARY KEY AUTOINCREMENT, component TEXT NOT NULL, question TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', answer TEXT NOT NULL, sources TEXT NOT NULL, proposed_update TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS security_scans (id INTEGER PRIMARY KEY AUTOINCREMENT, project_path TEXT NOT NULL, status TEXT NOT NULL, summary TEXT NOT NULL, findings TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS learning_review_runs (id INTEGER PRIMARY KEY AUTOINCREMENT, domain TEXT NOT NULL, status TEXT NOT NULL, added_count INTEGER NOT NULL DEFAULT 0, update_count INTEGER NOT NULL DEFAULT 0, details TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS fix_attempts (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, patch TEXT, test_result TEXT, activated INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS decision_log (id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, decision TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS retrieval_judgments (id INTEGER PRIMARY KEY AUTOINCREMENT, query TEXT NOT NULL, knowledge_id INTEGER NOT NULL, relevant INTEGER NOT NULL, score REAL NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS knowledge_audit (id INTEGER PRIMARY KEY AUTOINCREMENT, knowledge_id INTEGER NOT NULL, user_id INTEGER, action TEXT NOT NULL, details TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(knowledge_id) REFERENCES knowledge(id) ON DELETE CASCADE);

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
 knowledge_coverage_score REAL NOT NULL DEFAULT 0,
 verified_skill_score REAL NOT NULL DEFAULT 0,
 last_verified TEXT,
 UNIQUE(name,version)
);
CREATE TABLE IF NOT EXISTS skill_reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, skill_id INTEGER NOT NULL, reviewer_id INTEGER, outcome TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(skill_id) REFERENCES skills(id) ON DELETE CASCADE);
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
    if _write_blocked() and not path.parent.exists():
        raise PermissionError("MYAI_READ_ONLY blocks database directory creation.")
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
    if _write_blocked():
        return
    with connect() as conn:
        conn.create_function("normalize_search", 1, _normalize_search_text)
        conn.executescript(SCHEMA)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_attachments_session ON chat_attachments(session_id, id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_attachments_conversation ON chat_attachments(conversation_id, id)")
        cols=[r[1] for r in conn.execute("PRAGMA table_info(conversations)").fetchall()]
        if "session_id" not in cols: conn.execute("ALTER TABLE conversations ADD COLUMN session_id INTEGER")
        cols_sessions=[r[1] for r in conn.execute("PRAGMA table_info(chat_sessions)").fetchall()]
        if "pinned" not in cols_sessions: conn.execute("ALTER TABLE chat_sessions ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
        if "user_id" not in cols_sessions: conn.execute("ALTER TABLE chat_sessions ADD COLUMN user_id INTEGER")
        cols_experiences=[r[1] for r in conn.execute("PRAGMA table_info(learning_experiences)").fetchall()]
        for column, ddl in (("model_version","TEXT"),("provider","TEXT"),("tool_version","TEXT"),("skill_version","TEXT"),("environment_version","TEXT"),("compatibility","TEXT NOT NULL DEFAULT 'unknown'")):
            if column not in cols_experiences:
                conn.execute(f"ALTER TABLE learning_experiences ADD COLUMN {column} {ddl}")
        cols_learning=[r[1] for r in conn.execute("PRAGMA table_info(learning_sessions)").fetchall()]
        if "progress_percent" not in cols_learning: conn.execute("ALTER TABLE learning_sessions ADD COLUMN progress_percent REAL NOT NULL DEFAULT 0")
        if "phase" not in cols_learning: conn.execute("ALTER TABLE learning_sessions ADD COLUMN phase TEXT NOT NULL DEFAULT 'starting'")
        cols_skills=[r[1] for r in conn.execute("PRAGMA table_info(skills)").fetchall()]
        for column, ddl in (("concept_score","REAL NOT NULL DEFAULT 0"),("implementation_score","REAL NOT NULL DEFAULT 0"),("source_score","REAL NOT NULL DEFAULT 0"),("reliability_score","REAL NOT NULL DEFAULT 0"),("knowledge_coverage_score","REAL NOT NULL DEFAULT 0"),("verified_skill_score","REAL NOT NULL DEFAULT 0")):
            if column not in cols_skills:
                conn.execute(f"ALTER TABLE skills ADD COLUMN {column} {ddl}")
        cols_knowledge=[r[1] for r in conn.execute("PRAGMA table_info(knowledge)").fetchall()]
        if "content_hash" not in cols_knowledge: conn.execute("ALTER TABLE knowledge ADD COLUMN content_hash TEXT")
        if "verification_status" not in cols_knowledge: conn.execute("ALTER TABLE knowledge ADD COLUMN verification_status TEXT NOT NULL DEFAULT 'unverified'")
        if "verified_at" not in cols_knowledge: conn.execute("ALTER TABLE knowledge ADD COLUMN verified_at TEXT")
        if "verified_by" not in cols_knowledge: conn.execute("ALTER TABLE knowledge ADD COLUMN verified_by INTEGER")
        if "confidence" not in cols_knowledge: conn.execute("ALTER TABLE knowledge ADD COLUMN confidence REAL")
        for column, ddl in (("product","TEXT"),("version","TEXT"),("validity_status","TEXT NOT NULL DEFAULT 'unknown'"),("replaced_by_version","TEXT"),("compatibility","TEXT NOT NULL DEFAULT 'unknown'")):
            if column not in cols_knowledge: conn.execute(f"ALTER TABLE knowledge ADD COLUMN {column} {ddl}")
        admin_row = conn.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()
        if conn.execute("SELECT COUNT(*) FROM chat_sessions").fetchone()[0]==0 and conn.execute("SELECT COUNT(*) FROM conversations WHERE session_id IS NULL").fetchone()[0]:
            cur=conn.execute("INSERT INTO chat_sessions(title,user_id) VALUES(?,?)",("گفتگوی قبلی", admin_row[0] if admin_row else None))
            conn.execute("UPDATE conversations SET session_id=? WHERE session_id IS NULL",(cur.lastrowid,))
        elif admin_row:
            conn.execute("UPDATE chat_sessions SET user_id=? WHERE user_id IS NULL",(admin_row[0],))
        if admin_row:
            conn.execute("UPDATE conversations SET session_id=(SELECT id FROM chat_sessions WHERE user_id=? ORDER BY id LIMIT 1) WHERE session_id IS NULL",(admin_row[0],))
        if not conn.execute("SELECT 1 FROM schema_meta WHERE key='knowledge_dedup_v1'").fetchone():
            _deduplicate_knowledge(conn)
            conn.execute("INSERT OR REPLACE INTO schema_meta(key,value) VALUES('knowledge_dedup_v1','done')")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_knowledge_content_hash ON knowledge(content_hash)")
        conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
          INSERT INTO knowledge_fts(rowid,title,content,topic,source_url) VALUES(new.id,normalize_search(new.title),normalize_search(new.content),normalize_search(new.topic),normalize_search(new.source_url));
        END;
        CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
          INSERT INTO knowledge_fts(knowledge_fts,rowid,title,content,topic,source_url) VALUES('delete',old.id,normalize_search(old.title),normalize_search(old.content),normalize_search(old.topic),normalize_search(old.source_url));
        END;
        CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
          INSERT INTO knowledge_fts(knowledge_fts,rowid,title,content,topic,source_url) VALUES('delete',old.id,normalize_search(old.title),normalize_search(old.content),normalize_search(old.topic),normalize_search(old.source_url));
          INSERT INTO knowledge_fts(rowid,title,content,topic,source_url) VALUES(new.id,normalize_search(new.title),normalize_search(new.content),normalize_search(new.topic),normalize_search(new.source_url));
        END;
        """)
        if not conn.execute("SELECT 1 FROM schema_meta WHERE key='knowledge_fts_rebuilt_v1'").fetchone():
            conn.execute("INSERT INTO knowledge_fts(knowledge_fts) VALUES('delete-all')")
            for row in conn.execute("SELECT id,title,content,topic,source_url FROM knowledge").fetchall():
                conn.execute(
                    "INSERT INTO knowledge_fts(rowid,title,content,topic,source_url) VALUES(?,?,?,?,?)",
                    (row["id"], _normalize_search_text(row["title"]), _normalize_search_text(row["content"]), _normalize_search_text(row["topic"]), _normalize_search_text(row["source_url"] or "")),
                )
            conn.execute("INSERT INTO schema_meta(key,value) VALUES('knowledge_fts_rebuilt_v1','done')")

def execute(sql: str, params: tuple[Any, ...] = ()) -> int:
    if _write_blocked() and sql.lstrip().split(None, 1)[0].upper() in {"INSERT", "UPDATE", "DELETE", "REPLACE", "ALTER", "DROP", "CREATE"}:
        raise PermissionError("MYAI_READ_ONLY blocks database mutation.")
    with connect() as conn:
        cur = conn.execute(sql, params)
        conn.commit()
        return int(cur.lastrowid or 0)

def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]

def _semantic_duplicate(topic: str, title: str, content: str, digest: str, conn) -> dict[str, Any] | None:
    """Return the nearest existing knowledge item when semantic similarity exceeds the configured threshold."""
    try:
        from ..platform import cosine_similarity, ollama_embed
        from ..config import settings as runtime_settings
        from ..settings_store import get_setting
        threshold = float(get_setting("memory.duplicate_threshold", runtime_settings.knowledge_duplicate_threshold))
        query = f"{title}\n{content}\n{topic}"
        vector = ollama_embed(query, runtime_settings.embedding_model)
        rows = conn.execute(
            "SELECT k.id,k.title,k.topic,k.content,k.content_hash,e.embedding FROM knowledge k "
            "JOIN knowledge_embeddings e ON e.knowledge_id=k.id AND e.model=? "
            "WHERE k.content_hash<>? AND k.verification_status<>'deleted'",
            (runtime_settings.embedding_model, digest),
        ).fetchall()
        best = None
        for row in rows:
            try:
                score = cosine_similarity(vector, json.loads(row["embedding"]))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if score >= threshold and (best is None or score > best["similarity"]):
                best = {"id": int(row["id"]), "title": row["title"], "topic": row["topic"], "similarity": round(float(score), 6)}
        return best
    except Exception:
        return None


def remember_knowledge(topic: str, title: str, content: str, source_url: str | None = None, *, product: str | None = None, version: str | None = None, validity_status: str = "unknown", replaced_by_version: str | None = None, compatibility: str = "unknown") -> int:
    if _write_blocked():
        raise PermissionError("MYAI_READ_ONLY blocks database mutation.")
    digest = _knowledge_hash(topic, content)
    from ..settings_store import get_setting
    threshold = float(get_setting("memory.duplicate_threshold", settings.knowledge_duplicate_threshold))
    with connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS knowledge_audit (id INTEGER PRIMARY KEY AUTOINCREMENT, knowledge_id INTEGER NOT NULL, user_id INTEGER, action TEXT NOT NULL, details TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        row = conn.execute("SELECT id,source_url FROM knowledge WHERE content_hash=?", (digest,)).fetchone()
        if row:
            if not row["source_url"] and source_url:
                conn.execute("UPDATE knowledge SET source_url=? WHERE id=?", (source_url, row["id"]))
            conn.execute("INSERT INTO knowledge_audit(knowledge_id,user_id,action,details) VALUES(?,?,?,?)",
                         (row["id"], None, "duplicate_exact", "content_hash matched existing knowledge"))
            conn.commit()
            return int(row["id"])
        duplicate = _semantic_duplicate(topic, title, content, digest, conn)
        if duplicate:
            conn.execute("INSERT INTO knowledge_audit(knowledge_id,user_id,action,details) VALUES(?,?,?,?)",
                         (duplicate["id"], None, "duplicate_semantic_rejected",
                          json.dumps(duplicate, ensure_ascii=False, sort_keys=True)))
            conn.commit()
            raise ValueError(
                f"Semantic duplicate detected for knowledge {duplicate['id']} "
                f"(similarity={duplicate['similarity']}, threshold={threshold})."
            )
        cur = conn.execute("INSERT INTO knowledge(topic,title,content,source_url,content_hash,product,version,validity_status,replaced_by_version,compatibility) VALUES(?,?,?,?,?,?,?,?,?,?)",
                           (topic,title,content,source_url,digest,product,version,validity_status,replaced_by_version,compatibility))
        knowledge_id = int(cur.lastrowid or 0)
        conn.execute("INSERT INTO knowledge_audit(knowledge_id,user_id,action,details) VALUES(?,?,?,?)",
                     (knowledge_id, None, "create", "semantic duplicate check passed"))
        conn.commit()
        return knowledge_id


def purge_expired_knowledge() -> int:
    from ..settings_store import get_int
    days=max(1,get_int("memory.retention_days",int(getattr(settings,"memory_retention_days",365))))
    with connect() as conn:
        cur=conn.execute("DELETE FROM knowledge WHERE created_at < datetime('now', ?)",(f"-{days} days",))
        conn.commit()
        return int(cur.rowcount)

def search_knowledge(query: str, limit: int = 8) -> list[dict[str, Any]]:
    normalized_query = _normalize_search_text(query)
    tokens = [t for t in normalized_query.replace('"', " ").split() if t][:12]
    if not tokens: return []
    match = " ".join(f'"{t}"' for t in tokens)
    return fetch_all(
        """SELECT k.id,k.topic,k.title,k.content,k.source_url,k.verification_status,k.confidence,k.product,k.version,k.validity_status,k.replaced_by_version,k.compatibility,k.created_at,
                  bm25(knowledge_fts) AS rank
           FROM knowledge_fts JOIN knowledge k ON k.id=knowledge_fts.rowid
           WHERE knowledge_fts MATCH ? ORDER BY rank, k.id DESC LIMIT ?""",
        (match, limit),
    )
