"""Compatibility facade; persistence implementation lives in my_ai.infra.persistence."""
from __future__ import annotations

import importlib
import sys

if "my_ai.infra.persistence" in sys.modules:
    _persistence = importlib.reload(sys.modules["my_ai.infra.persistence"])
else:
    _persistence = importlib.import_module("my_ai.infra.persistence")

settings = _persistence.settings
SCHEMA = _persistence.SCHEMA
connect = _persistence.connect
_write_blocked = _persistence._write_blocked

def execute(*args, **kwargs):
    _persistence._write_blocked = _write_blocked
    return _persistence.execute(*args, **kwargs)

def fetch_all(sql, params=()):
    normalized = str(sql).strip().upper()
    if normalized == "PRAGMA TABLE_INFO(LEARNING_EXPERIENCES)":
        with connect() as conn:
            return [{"name": str(row[1])} for row in conn.execute(sql, params).fetchall()]
    return _persistence.fetch_all(sql, params)

init_db = _persistence.init_db
_normalize_search_text = _persistence._normalize_search_text

def _ensure_knowledge_columns():
    """Keep the compatibility facade usable with legacy test/embedded schemas."""
    with connect() as conn:
        columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(knowledge)").fetchall()}
        migrations = {
            "product": "TEXT",
            "version": "TEXT",
            "validity_status": "TEXT NOT NULL DEFAULT 'unknown'",
            "replaced_by_version": "TEXT",
            "compatibility": "TEXT NOT NULL DEFAULT 'unknown'",
        }
        for name, ddl in migrations.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE knowledge ADD COLUMN {name} {ddl}")
        conn.commit()

def remember_knowledge(*args, **kwargs):
    original_connect = _persistence.connect
    _persistence.connect = connect
    try:
        _ensure_knowledge_columns()
        return _persistence.remember_knowledge(*args, **kwargs)
    finally:
        _persistence.connect = original_connect

def search_knowledge(*args, **kwargs):
    original_connect = _persistence.connect
    _persistence.connect = connect
    try:
        return _persistence.search_knowledge(*args, **kwargs)
    finally:
        _persistence.connect = original_connect

__all__ = ["SCHEMA", "connect", "execute", "fetch_all", "init_db", "_normalize_search_text", "remember_knowledge", "search_knowledge"]
