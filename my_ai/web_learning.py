from __future__ import annotations

import json
from datetime import datetime, timezone

from .db import execute, fetch_all
from .dynamic_learning import _normalize_topics, _persist, ensure_domain
from .curriculum import LANGUAGE_CURRICULA, LANGUAGE_SOURCES
from .memory import remember
from .web_learner import WebLearner


def _pending_table():
    execute("""CREATE TABLE IF NOT EXISTS web_learning_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT
    )""")


def create_pending(session_id: int, question: str) -> int:
    _pending_table()
    rows = fetch_all("SELECT id FROM web_learning_requests WHERE session_id=? AND status='pending' ORDER BY id DESC LIMIT 1", (session_id,))
    if rows:
        execute("UPDATE web_learning_requests SET question=?,created_at=CURRENT_TIMESTAMP WHERE id=?", (question, rows[0]["id"]))
        return int(rows[0]["id"])
    return int(execute("INSERT INTO web_learning_requests(session_id,question) VALUES(?,?)", (session_id, question)))


def pending(session_id: int):
    _pending_table()
    rows = fetch_all("SELECT * FROM web_learning_requests WHERE session_id=? AND status='pending' ORDER BY id DESC LIMIT 1", (session_id,))
    return rows[0] if rows else None


def learn_confirmed(session_id: int, question: str, llm, web: WebLearner) -> dict:
    _pending_table()
    item = pending(session_id)
    question = str(question or (item["question"] if item else "")).strip()
    if not question:
        return {"status": "no_pending_request"}

    evidence = []
    try:
        results = web.search(question, limit=8)
    except Exception as exc:
        return {"status": "error", "error": f"جستجوی اینترنتی انجام نشد: {exc}"}

    for result in results:
        try:
            title, text = web.fetch(result["url"])
            evidence.append({"title": title, "url": result["url"], "text": text[:7000]})
        except Exception:
            continue

    if not evidence:
        return {"status": "error", "error": "منبع قابل‌استفاده‌ای از اینترنت پیدا نشد."}

    prompt = (
        "Using ONLY the supplied web evidence, extract reliable learning material for the user's question. "
        "Return JSON only with keys: domain, topic, goal, summary, sources. "
        "domain should be an existing learning domain when one clearly fits; otherwise create a concise new domain. "
        "topic must be a concrete curriculum heading. "
        "summary must be useful teaching material, not a vague summary. "
        "sources must contain only URLs present in the evidence. "
        f"QUESTION: {question}\nEVIDENCE: {json.dumps(evidence, ensure_ascii=False)[:30000]}"
    )
    try:
        data = json.loads(llm.chat(prompt, system="You are a conservative technical curriculum researcher. Never invent sources or facts."))
    except Exception as exc:
        return {"status": "error", "error": f"یادگیری از منابع وب تحلیل نشد: {exc}"}

    domain = str(data.get("domain") or "").strip()
    topic = str(data.get("topic") or "").strip()
    goal = str(data.get("goal") or "").strip()
    summary = str(data.get("summary") or "").strip()
    sources = [str(x) for x in data.get("sources", []) if str(x) in {e["url"] for e in evidence}]
    if not domain or not topic or not summary:
        return {"status": "error", "error": "نتیجه وب برای ساخت سرفصل کافی نبود."}

    canonical = ensure_domain(domain, llm)
    topics = list(LANGUAGE_CURRICULA.get(canonical, []))
    if not any(str(x.get("topic","")).casefold() == topic.casefold() for x in topics):
        topics.extend(_normalize_topics([{"topic": topic, "goal": goal or summary[:300]}]))
    existing_sources = list(LANGUAGE_SOURCES.get(canonical, []))
    for source in sources:
        if source not in existing_sources:
            existing_sources.append(source)
    LANGUAGE_CURRICULA[canonical] = topics
    LANGUAGE_SOURCES[canonical] = existing_sources
    _persist(canonical, topics, existing_sources, None)

    remember(topic, f"Web learned: {topic}", summary, sources[0] if sources else None)
    execute("UPDATE web_learning_requests SET status='completed',completed_at=? WHERE session_id=? AND status='pending'",
            (datetime.now(timezone.utc).isoformat(), session_id))
    return {"status": "learned", "domain": canonical, "topic": topic, "sources": sources}
