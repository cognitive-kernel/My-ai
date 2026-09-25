from __future__ import annotations

from .curriculum import LANGUAGE_CURRICULA, source_urls, canonical_language
from .topic_resources import supplementary_source_urls
from .db import execute, fetch_all

def topic_source_urls(language: str, topic: str) -> list[str]:
    urls = supplementary_source_urls(language, topic) + source_urls(language)
    return list(dict.fromkeys(str(url) for str in urls if str(url).startswith(("http://", "https://"))))

def ensure_source_tracking() -> None:
    execute("""CREATE TABLE IF NOT EXISTS learning_source_history (
        language TEXT NOT NULL, topic TEXT NOT NULL, url TEXT NOT NULL, learned_at TEXT,
        PRIMARY KEY(language, topic, url))""")

def baseline_completed_sources(language: str) -> None:
    ensure_source_tracking()
    language = canonical_language(language)
    completed = fetch_all("SELECT topic FROM learning_sessions WHERE language=? AND status='completed'", (language,))
    for row in completed:
        topic = str(row["topic"])
        existing = fetch_all("SELECT 1 FROM learning_source_history WHERE language=? AND topic=? LIMIT 1", (language, topic))
        if existing:
            continue
        # Existing broad domain sources are the legacy baseline. Topic-specific
        # supplementary sources are intentionally left pending on first migration,
        # so a completed course learns the newly introduced supplementary material once.
        for url in source_urls(language):
            if str(url).startswith(("http://", "https://")):
                execute("INSERT OR IGNORE INTO learning_source_history(language,topic,url,learned_at) VALUES(?,?,?,CURRENT_TIMESTAMP)", (language, topic, url))

def find_unlearned_new_sources(language: str) -> list[dict]:
    ensure_source_tracking()
    language = canonical_language(language)
    baseline_completed_sources(language)
    result = []
    for item in LANGUAGE_CURRICULA.get(language, []):
        topic = str(item.get("topic", ""))
        if not topic:
            continue
        for url in topic_source_urls(language, topic):
            rows = fetch_all("SELECT learned_at FROM learning_source_history WHERE language=? AND topic=? AND url=?", (language, topic, url))
            if not rows:
                execute("INSERT OR IGNORE INTO learning_source_history(language,topic,url,learned_at) VALUES(?,?,?,NULL)", (language, topic, url))
                result.append({"topic": topic, "url": url})
            elif rows[0]["learned_at"] is None:
                result.append({"topic": topic, "url": url})
    return result

def mark_sources_learned(language: str, topic: str, urls: list[str]) -> None:
    ensure_source_tracking()
    for url in urls:
        if str(url).startswith(("http://", "https://")):
            execute("""INSERT INTO learning_source_history(language,topic,url,learned_at)
                       VALUES(?,?,?,CURRENT_TIMESTAMP)
                       ON CONFLICT(language,topic,url) DO UPDATE SET learned_at=CURRENT_TIMESTAMP""",
                    (canonical_language(language), topic, url))
