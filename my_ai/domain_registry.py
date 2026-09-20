from __future__ import annotations

import json

from .curriculum import LANGUAGE_CURRICULA, LANGUAGE_SOURCES
from .db import execute, fetch_all


def load_saved_domains() -> list[str]:
    execute("""CREATE TABLE IF NOT EXISTS learning_domains (
        name TEXT PRIMARY KEY,
        topics_json TEXT NOT NULL,
        sources_json TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_review_at TEXT,
        next_review_at TEXT
    )""")
    names = []
    for row in fetch_all("SELECT name,topics_json,sources_json FROM learning_domains"):
        name = str(row["name"] or "").strip()
        if not name:
            continue
        try:
            topics = json.loads(row["topics_json"] or "[]")
            sources = json.loads(row["sources_json"] or "[]")
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(topics, list):
            LANGUAGE_CURRICULA[name] = topics
            LANGUAGE_SOURCES[name] = [str(x) for x in sources if str(x).startswith(("http://", "https://"))]
            names.append(name)
    return names
