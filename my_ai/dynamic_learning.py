from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from .curriculum import LANGUAGE_ALIASES, LANGUAGE_CURRICULA, LANGUAGE_SOURCES, canonical_language
from .db import execute, fetch_all

REVIEW_DAYS = 7


def _ensure_storage() -> None:
    execute("""CREATE TABLE IF NOT EXISTS learning_domains (
        name TEXT PRIMARY KEY,
        topics_json TEXT NOT NULL,
        sources_json TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_review_at TEXT,
        next_review_at TEXT
    )""")


def _normalize_topics(items):
    topics = []
    seen = set()
    for index, item in enumerate(items or [], 1):
        if not isinstance(item, dict):
            continue
        topic = str(item.get("topic", "")).strip()
        goal = str(item.get("goal", "")).strip()
        if not topic or topic.lower() in seen:
            continue
        seen.add(topic.lower())
        topics.append({"order": index, "topic": topic, "goal": goal or f"Master {topic} from fundamentals through advanced practice."})
    return topics


def _merge_topics(base, additions):
    merged = _normalize_topics(base)
    seen = {str(x["topic"]).lower() for x in merged}
    for item in _normalize_topics(additions):
        key = str(item["topic"]).lower()
        if key in seen:
            continue
        item["order"] = len(merged) + 1
        merged.append(item)
        seen.add(key)
    return merged


def _load_saved(name):
    _ensure_storage()
    rows = fetch_all("SELECT topics_json,sources_json FROM learning_domains WHERE name=?", (name,))
    if not rows:
        return None
    try:
        topics = _normalize_topics(json.loads(rows[0]["topics_json"]))
        sources = [str(x) for x in json.loads(rows[0]["sources_json"] or "[]") if str(x).startswith(("http://", "https://"))]
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    LANGUAGE_CURRICULA[name] = topics
    LANGUAGE_SOURCES[name] = sources
    return topics


def _persist(name, topics, sources, next_review_at=None):
    _ensure_storage()
    payload = json.dumps(_normalize_topics(topics), ensure_ascii=False)
    src = json.dumps(list(dict.fromkeys(sources)), ensure_ascii=False)
    execute(
        """INSERT INTO learning_domains(name,topics_json,sources_json,next_review_at)
           VALUES(?,?,?,?)
           ON CONFLICT(name) DO UPDATE SET topics_json=excluded.topics_json,
             sources_json=excluded.sources_json,updated_at=CURRENT_TIMESTAMP,
             next_review_at=COALESCE(excluded.next_review_at,learning_domains.next_review_at)""",
        (name, payload, src, next_review_at),
    )


def _fallback_curriculum(name):
    phases = [
        ("Fundamentals", "Terminology, syntax, core concepts and basic usage"),
        ("Core concepts", "Essential concepts, APIs, data structures and common operations"),
        ("Intermediate practice", "Realistic workflows, patterns and error handling"),
        ("Advanced concepts", "Advanced features, internals, performance and edge cases"),
        ("Architecture", "Design, modularity, scalability and maintainability"),
        ("Security", "Threats, secure defaults, validation and defensive practices"),
        ("Testing", "Unit, integration, regression and failure-driven testing"),
        ("Debugging", "Diagnostics, profiling, root-cause analysis and recovery"),
        ("Performance", "Benchmarking, profiling, optimization and resource management"),
        ("Production", "Deployment, monitoring, reliability and operations"),
        ("Internals", "Runtime implementation, protocols, compilers or engines where applicable"),
        ("Expert patterns", "Advanced patterns, trade-offs and ecosystem best practices"),
        ("Real project", "Build a complete production-style project from requirements to tests"),
        ("Capstone", "Independent expert-level implementation, debugging and optimization"),
    ]
    return [{"order": i, "topic": f"{name}: {title}", "goal": goal} for i, (title, goal) in enumerate(phases, 1)]


def ensure_domain(name, llm=None):
    name = str(name or "").strip()
    if not name:
        return None
    canonical = canonical_language(name)
    static_topics = list(LANGUAGE_CURRICULA.get(canonical, []))
    if canonical in LANGUAGE_CURRICULA and llm is None:
        return canonical
    saved = _load_saved(name)
    if saved:
        if static_topics:
            merged = _merge_topics(static_topics, saved)
            LANGUAGE_CURRICULA[canonical] = merged
            _persist(canonical, merged, LANGUAGE_SOURCES.get(canonical, []))
        return canonical if canonical in LANGUAGE_CURRICULA else name

    topics = []
    sources = []
    if llm is not None:
        prompt = (
            "Build a comprehensive curriculum for the requested subject from absolute beginner to expert/advanced level. "
            "Cover prerequisites, fundamentals, intermediate concepts, advanced concepts, internals, security, testing, "
            "debugging, performance, architecture, production practices, ecosystem/tooling, and a capstone project where applicable. Every domain must progress from absolute beginner to expert and each advanced claim must be paired with exercises, executable verification, tests or benchmarks where applicable, security review, and a final project/capstone. "
            "Return JSON only with keys topics and sources. topics must be an array of objects with topic and goal. "
            "Prefer 24-60 concrete, non-duplicate topics. sources must contain official documentation URLs when known.\n"
            f"SUBJECT: {name}"
        )
        try:
            raw = llm.chat(prompt, system="You are a rigorous curriculum architect. Return valid JSON only.")
            data = json.loads(raw)
            topics = _normalize_topics(data.get("topics", [])) if isinstance(data, dict) else []
            sources = [str(x) for x in (data.get("sources", []) if isinstance(data, dict) else []) if str(x).startswith(("http://", "https://"))]
        except (TypeError, ValueError, json.JSONDecodeError):
            topics = []
    if static_topics:
        topics = _merge_topics(static_topics, topics)
        if not sources:
            sources = list(LANGUAGE_SOURCES.get(canonical, []))
        key = canonical
    else:
        if not topics:
            topics = _fallback_curriculum(name)
        key = name
    _persist(key, topics, sources, (datetime.now(timezone.utc) + timedelta(days=REVIEW_DAYS)).isoformat())
    LANGUAGE_CURRICULA[key] = topics
    LANGUAGE_SOURCES[key] = sources
    return key


def resolve_learning_target(message, fallback="Python"):
    """Resolve a learning subject without substring-matching short aliases inside words."""
    text = str(message or "").strip()
    low = text.casefold()

    # Match aliases as complete words/phrases. This prevents the C alias from
    # matching unrelated subjects such as "Cisco".
    for alias, canonical in sorted(LANGUAGE_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        alias_text = str(alias).strip().casefold()
        if not alias_text:
            continue
        if re.search(rf"(?<![\w]){re.escape(alias_text)}(?![\w])", low, re.IGNORECASE):
            return canonical

    patterns = [
        r"(?:یاد\s*بگیر|یادگیری|شروع\s*یادگیری|learn|study)\s+(?:the\s+)?(.+)$",
        r"(?:یاد\s*بده|teach\s+me)\s+(.+)$",
        r"^(.+?)\s+(?:یاد\s*بگیر|یاد\s*بده)$",
        r"^(.+?)\s+(?:learn|study)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            target = re.sub(r"[.!?،]+$", "", match.group(1)).strip()
            target = re.sub(r"^(?:زبان|موضوع|language|topic)\s+", "", target, flags=re.IGNORECASE).strip()
            if target:
                return target
    return fallback


def due_domains(now=None):
    _ensure_storage()
    now = now or datetime.now(timezone.utc)
    rows = fetch_all("SELECT name,next_review_at FROM learning_domains WHERE next_review_at IS NOT NULL")
    result = []
    for row in rows:
        try:
            due = datetime.fromisoformat(str(row["next_review_at"]).replace("Z", "+00:00"))
            if due <= now:
                result.append(str(row["name"]))
        except ValueError:
            result.append(str(row["name"]))
    return result


def mark_reviewed(name, topics, sources, now=None):
    now = now or datetime.now(timezone.utc)
    _persist(name, topics, sources, (now + timedelta(days=REVIEW_DAYS)).isoformat())
    execute("UPDATE learning_domains SET last_review_at=?,next_review_at=? WHERE name=?", (now.isoformat(), (now + timedelta(days=REVIEW_DAYS)).isoformat(), name))


def weekly_review(name, web, llm, now=None):
    name = str(name).strip()
    if not name or name not in LANGUAGE_CURRICULA or not web or not llm:
        return {"status": "skipped", "reason": "domain unavailable"}
    topics = list(LANGUAGE_CURRICULA.get(name, []))
    sources = list(LANGUAGE_SOURCES.get(name, []))
    evidence = []
    for source in sources[:12]:
        try:
            title, text = web.fetch(source)
            evidence.append({"title": title, "url": source, "text": text[:5000]})
        except Exception as exc:
            evidence.append({"url": source, "error": str(exc)})
    if not evidence:
        try:
            evidence = web.search(f"{name} latest release documentation changes", limit=6)
        except Exception:
            evidence = []
    prompt = (
        "Review the following current web evidence for a completed learning domain. Identify genuinely new material that "
        "should be learned since the previous curriculum. Prefer official documentation, standards, release notes and maintainer documentation. "
        "Distinguish new topics from updates to existing topics. Do not invent releases or facts. Return JSON only: "
        '{"new_topics":[{"topic":"...","goal":"..."}],"updates":[{"topic":"...","reason":"..."}]}.'
        f"\nDOMAIN: {name}\nCURRENT TOPICS: {json.dumps(topics, ensure_ascii=False)}\nWEB EVIDENCE: {json.dumps(evidence, ensure_ascii=False)[:24000]}"
    )
    try:
        data = json.loads(llm.chat(prompt, system="You are a conservative technical update reviewer. Return valid JSON only."))
    except (TypeError, ValueError, json.JSONDecodeError):
        mark_reviewed(name, topics, sources, now)
        return {"status": "reviewed", "added": [], "updates": []}
    additions = _normalize_topics(data.get("new_topics", []) if isinstance(data, dict) else [])
    existing = {str(x["topic"]).lower() for x in topics}
    added = []
    for item in additions:
        if item["topic"].lower() not in existing:
            item["order"] = len(topics) + 1
            topics.append(item)
            existing.add(item["topic"].lower())
            added.append(item)
    mark_reviewed(name, topics, sources, now)
    LANGUAGE_CURRICULA[name] = topics
    return {"status": "reviewed", "added": added, "updates": data.get("updates", []) if isinstance(data, dict) else []}
