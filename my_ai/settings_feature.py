from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from .auth import require_admin, require_user, audit
from .db import connect, execute, fetch_all, init_db
from .git_connector import GitHubConnector
from .llm import create_llm
from .settings_store import get_setting, set_setting, get_bool, get_int, get_github_settings

router = APIRouter(tags=["settings"])
_workers = ThreadPoolExecutor(max_workers=1, thread_name_prefix="myai-learning")
_running: set[int] = set()

SCHEMA = """
CREATE TABLE IF NOT EXISTS custom_courses (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL UNIQUE,
 description TEXT NOT NULL DEFAULT '',
 active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS custom_course_topics (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 course_id INTEGER NOT NULL,
 topic_order INTEGER NOT NULL,
 title TEXT NOT NULL,
 goal TEXT NOT NULL DEFAULT '',
 source_url TEXT,
 FOREIGN KEY(course_id) REFERENCES custom_courses(id) ON DELETE CASCADE,
 UNIQUE(course_id,topic_order)
);
CREATE TABLE IF NOT EXISTS custom_course_progress (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 course_id INTEGER NOT NULL,
 topic_id INTEGER NOT NULL,
 status TEXT NOT NULL DEFAULT 'planned',
 progress_percent REAL NOT NULL DEFAULT 0,
 phase TEXT NOT NULL DEFAULT 'planned',
 lesson TEXT,
 score REAL,
 updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 last_attempt_at TEXT,
 UNIQUE(course_id,topic_id),
 FOREIGN KEY(course_id) REFERENCES custom_courses(id) ON DELETE CASCADE,
 FOREIGN KEY(topic_id) REFERENCES custom_course_topics(id) ON DELETE CASCADE
);
"""


class CourseRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    topics: list[dict[str, str]] = Field(min_length=1, max_length=100)

class CourseTopicRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    goal: str = Field(default="", max_length=2000)
    source_url: str = Field(default="", max_length=1000)

class CourseUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)


class TokenRequest(BaseModel):
    token: str = Field(default="", max_length=10000)

class GithubConfigRequest(BaseModel):
    api_url: str = Field(min_length=8, max_length=500)
    repository: str = Field(min_length=3, max_length=300)
    username: str = Field(default="", max_length=200)

class FeatureSettingsRequest(BaseModel):
    self_update_enabled: bool = False
    self_update_approved: bool = False
    self_update_health_url: str = ""
    self_repair_enabled: bool = True
    self_repair_require_approval: bool = True
    learning_fast_enabled: bool = False
    learning_interval_seconds: int = 3600
    learning_max_retries: int = 5

class ToolPermissionRequest(BaseModel):
    user_id: int
    tool_name: str = Field(min_length=1, max_length=120)
    action: str = Field(min_length=1, max_length=40)
    allowed: bool

class ResourceSettingsRequest(BaseModel):
    cpu_percent: float = 70.0
    cpu_threads: int = 8
    ram_percent: float = 80.0
    gpu_layers: int = 0

class ImageSettingsRequest(BaseModel):
    enabled: bool = True
    provider: str = "automatic1111"
    url: str = "http://127.0.0.1:7860"
    model: str = ""
    sampler: str = "DPM++ 2M Karras"
    steps: int = 32
    cfg: float = 7.0
    hires: bool = True
    hires_scale: float = 1.5
    denoise: float = 0.35
    hr_upscaler: str = "Latent"
    default_size: str = "1024x1024"
    negative_prompt: str = ""

class LogSettingsRequest(BaseModel):
    level: str = "WARNING"


def _setup() -> None:
    init_db()
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learning_domains (
                name TEXT PRIMARY KEY,
                topics_json TEXT NOT NULL,
                sources_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_review_at TEXT,
                next_review_at TEXT,
                auto_learn INTEGER NOT NULL DEFAULT 1
            )
        """)
        # One-time migration: purge the retired Cisco training artifacts that may
        # exist from older builds. Once complete, Cisco is a normal supported
        # curriculum again and must never be purged on later startups.
        migration_key = "migration.legacy_cisco_cleanup_v1"
        migration_done = str(get_setting(migration_key, "")).strip().lower() == "done"
        if not migration_done:
            ids = [int(row["id"]) for row in conn.execute("SELECT id FROM custom_courses WHERE lower(trim(name))='cisco'").fetchall()]
            if ids:
                marks = ",".join("?" for _ in ids)
                conn.execute(f"DELETE FROM custom_course_progress WHERE course_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM custom_course_topics WHERE course_id IN ({marks})", ids)
                conn.execute(f"DELETE FROM custom_courses WHERE id IN ({marks})", ids)
            conn.execute("DELETE FROM learning_workers WHERE lower(language)='cisco'")
            conn.execute("DELETE FROM learning_sessions WHERE lower(language)='cisco'")
            conn.execute("DELETE FROM learning_runtime WHERE lower(COALESCE(language,''))='cisco'")
            conn.execute("DELETE FROM learning_domains WHERE lower(name) LIKE '%cisco%'")
            conn.execute("DELETE FROM knowledge_embeddings WHERE knowledge_id IN (SELECT id FROM knowledge WHERE lower(topic) LIKE '%cisco%' OR lower(title) LIKE '%cisco%' OR lower(content) LIKE '%cisco%' OR lower(COALESCE(source_url,'')) LIKE '%cisco%')")
            conn.execute("DELETE FROM knowledge_audit WHERE knowledge_id IN (SELECT id FROM knowledge WHERE lower(topic) LIKE '%cisco%' OR lower(title) LIKE '%cisco%' OR lower(content) LIKE '%cisco%' OR lower(COALESCE(source_url,'')) LIKE '%cisco%')")
            conn.execute("DELETE FROM knowledge WHERE lower(topic) LIKE '%cisco%' OR lower(title) LIKE '%cisco%' OR lower(content) LIKE '%cisco%' OR lower(COALESCE(source_url,'')) LIKE '%cisco%'")
            conn.commit()
            set_setting(migration_key, "done")
    for row in fetch_all("SELECT id FROM custom_courses WHERE active=1"):
        _ensure_custom_review_schedule(int(row["id"]))


def _course(course_id: int) -> dict[str, Any] | None:
    rows = fetch_all("SELECT * FROM custom_courses WHERE id=?", (course_id,))
    return rows[0] if rows else None


def _progress(course_id: int) -> list[dict[str, Any]]:
    return fetch_all("""SELECT t.id,t.topic_order,t.title,t.goal,t.source_url,
        COALESCE(p.status,'planned') status,COALESCE(p.progress_percent,0) progress_percent,
        COALESCE(p.phase,'planned') phase,p.lesson,p.score,p.updated_at,p.last_attempt_at
        FROM custom_course_topics t LEFT JOIN custom_course_progress p ON p.topic_id=t.id
        WHERE t.course_id=? ORDER BY t.topic_order""", (course_id,))


def _ensure_custom_review_schedule(course_id: int) -> None:
    course = _course(course_id)
    if not course:
        return
    execute("""CREATE TABLE IF NOT EXISTS learning_domains (
        name TEXT PRIMARY KEY,
        topics_json TEXT NOT NULL,
        sources_json TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_review_at TEXT,
        next_review_at TEXT,
        auto_learn INTEGER NOT NULL DEFAULT 1
    )""")
    try:
        execute("ALTER TABLE learning_domains ADD COLUMN auto_learn INTEGER NOT NULL DEFAULT 1")
    except Exception:
        pass
    topics = [
        {"order": int(x["topic_order"]), "topic": str(x["title"]), "goal": str(x["goal"] or "")}
        for x in _progress(course_id)
    ]
    sources = [str(x["source_url"]) for x in _progress(course_id) if x.get("source_url")]
    next_review = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    execute(
        """INSERT INTO learning_domains(name,topics_json,sources_json,next_review_at,auto_learn)
           VALUES(?,?,?,?,1)
           ON CONFLICT(name) DO UPDATE SET
           topics_json=excluded.topics_json,sources_json=excluded.sources_json,
           updated_at=CURRENT_TIMESTAMP,
           next_review_at=COALESCE(NULLIF(learning_domains.next_review_at,''), excluded.next_review_at),
           auto_learn=1""",
        (f"custom_course:{course_id}", json.dumps(topics, ensure_ascii=False), json.dumps(sources, ensure_ascii=False), next_review),
    )


def _summary(course_id: int) -> dict[str, Any]:
    items = _progress(course_id)
    completed = sum(1 for x in items if x["status"] == "completed")
    current = next((x for x in items if x["status"] == "started"), None)
    if current is None:
        current = next((x for x in items if x["status"] != "completed"), None)
    overall = round(((completed + (float(current["progress_percent"]) / 100 if current else 0)) / len(items) * 100), 1) if items else 0
    return {"course_id": course_id, "total_topics": len(items), "completed_topics": completed, "progress_percent": overall, "current": current, "topics": items}


def _review_custom_course(course_id: int, web, llm) -> dict[str, Any]:
    """Weekly web review for custom courses: discover new topics and refresh changed topics."""
    course = _course(course_id)
    if not course or not course["active"]:
        return {"status": "skipped", "added": [], "updated": []}
    rows = _progress(course_id)
    topics = [{"topic": str(x["title"]), "goal": str(x["goal"] or "")} for x in rows]
    evidence = []
    seen_urls: set[str] = set()
    candidates: list[str] = []
    for row in rows[:12]:
        url = str(row.get("source_url") or "").strip()
        if url and url not in seen_urls:
            seen_urls.add(url)
            candidates.append(url)
    try:
        search_results = web.search(
            f"{course['name']} latest documentation updates new topics",
            limit=8,
        )
        for item in search_results:
            url = str(item.get("url") or "").strip()
            if url.startswith(("http://", "https://")) and url not in seen_urls:
                seen_urls.add(url)
                candidates.append(url)
    except Exception:
        pass
    for url in candidates[:16]:
        try:
            title, source = web.fetch(url)
            evidence.append({"title": title, "url": url, "text": str(source)[:5000]})
        except Exception as exc:
            evidence.append({"url": url, "error": str(exc)})
    if not evidence:
        return {"status": "reviewed", "added": [], "updated": []}
    prompt = (
        "Review current web evidence for a custom learning course. Identify only genuinely new "
        "learning topics or substantive changes to existing topics. Do not invent facts. Prefer "
        "official documentation, standards, maintainers, universities, regulators, exchanges, or "
        "other authoritative sources. Return JSON only with keys new_topics and updated_topics. "
        "new_topics: objects with title, goal, source_url. updated_topics: objects with title, "
        "reason, source_url. Only include an updated topic when the evidence shows a substantive "
        "change or important new material that should trigger relearning.\n"
        f"COURSE: {course['name']}\nCURRENT TOPICS: {json.dumps(topics, ensure_ascii=False)}\n"
        f"WEB EVIDENCE: {json.dumps(evidence, ensure_ascii=False)[:30000]}"
    )
    try:
        data = json.loads(llm.chat(prompt, system="You are a conservative technical curriculum reviewer. Return valid JSON only."))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {"status": "reviewed", "added": [], "updated": []}
    existing = {str(x["title"]).strip().casefold(): x for x in rows}
    added = []
    updated = []
    next_order = max([int(x["topic_order"]) for x in rows] or [0]) + 1
    for item in data.get("new_topics", []) if isinstance(data, dict) else []:
        title = str(item.get("title") or "").strip()
        goal = str(item.get("goal") or "").strip()
        source_url = str(item.get("source_url") or "").strip()
        if not title or title.casefold() in existing:
            continue
        cur = execute(
            "INSERT INTO custom_course_topics(course_id,topic_order,title,goal,source_url) VALUES(?,?,?,?,?)",
            (course_id, next_order, title, goal, source_url or None),
        )
        if cur:
            execute("INSERT INTO custom_course_progress(course_id,topic_id,status,progress_percent,phase) VALUES(?,?,?,?,?)",
                    (course_id, cur, "planned", 0, "planned"))
            added.append({"title": title, "goal": goal, "source_url": source_url})
            existing[title.casefold()] = {"id": cur}
            next_order += 1
    for item in data.get("updated_topics", []) if isinstance(data, dict) else []:
        title = str(item.get("title") or "").strip()
        current = existing.get(title.casefold())
        if not current:
            continue
        source_url = str(item.get("source_url") or "").strip()
        if source_url:
            execute("UPDATE custom_course_topics SET source_url=? WHERE id=?", (source_url, int(current["id"])))
        execute(
            "UPDATE custom_course_progress SET status='planned',progress_percent=0,phase='planned',updated_at=CURRENT_TIMESTAMP WHERE topic_id=?",
            (int(current["id"]),),
        )
        updated.append({"title": title, "reason": str(item.get("reason") or ""), "source_url": source_url})
    if added or updated:
        _ensure_custom_review_schedule(course_id)
    return {"status": "reviewed", "added": added, "updated": updated}


def _set_topic(topic_id: int, status: str, progress: float, phase: str, lesson: str | None = None, score: float | None = None) -> None:
    execute("UPDATE custom_course_progress SET status=?,progress_percent=?,phase=?,lesson=COALESCE(?,lesson),score=COALESCE(?,score),updated_at=CURRENT_TIMESTAMP WHERE topic_id=?", (status, max(0,min(100,float(progress))), phase, lesson, score, topic_id))


def _learn_topic(course_id: int, topic: dict[str, Any]) -> None:
    topic_id = int(topic["id"])
    execute("UPDATE custom_course_progress SET last_attempt_at=CURRENT_TIMESTAMP WHERE topic_id=?", (topic_id,))
    _set_topic(topic_id, "started", 5, "understanding")
    llm = create_llm("general")
    prompt = ("Teach this study unit accurately and practically. Explain prerequisites, concepts, technical examples and verification steps, common mistakes, safe lab exercises, and a short mastery checklist. "
              "Do not invent platform-specific behavior; state uncertainty when applicable.\n"
              f"COURSE: {(_course(course_id) or {}).get('name', 'Custom Course')}\nTOPIC: {topic['title']}\nGOAL: {topic['goal']}\nOFFICIAL SOURCE: {topic.get('source_url') or 'none'}")
    _set_topic(topic_id, "started", 25, "lesson")
    lesson = llm.chat(prompt, system="You are a rigorous technical instructor. Return a concise but technically precise lesson.")
    _set_topic(topic_id, "started", 70, "assessment", lesson=lesson)
    raw = llm.chat("Return only a numeric score from 0 to 100 for whether this lesson adequately covers the stated goal. GOAL:" + topic["goal"] + "\nLESSON:" + lesson)
    match = re.search(r"(?<!\d)(100|\d{1,2})(?!\d)", raw)
    score = float(match.group(1)) if match else 0.0
    from .memory import remember
    knowledge_id = remember(topic["title"], f"Custom Course lesson: {topic['title']}", lesson, topic.get("source_url") or None)
    execute("UPDATE knowledge SET confidence=? WHERE id=?", (max(0.0, min(1.0, score / 100.0)), knowledge_id))
    _set_topic(topic_id, "completed", 100, "completed", score=score)
    audit(None, "learning", "execute", "200", f"custom-course:{course_id}:topic:{topic_id}")


def _run_course(course_id: int) -> None:
    if course_id in _running:
        return
    _running.add(course_id)
    try:
        while True:
            course = _course(course_id)
            if not course or not course["active"]:
                return
            rows = _progress(course_id)
            topic = next((x for x in rows if x["status"] not in {"completed", "paused"}), None)
            if not topic:
                return
            try:
                _learn_topic(course_id, topic)
            except Exception as exc:
                _set_topic(int(topic["id"]), "paused", max(5, float(topic["progress_percent"])), "error", lesson=f"Learning paused after an error: {exc}")
                return
            if not fetch_all("SELECT id FROM custom_course_topics t WHERE t.course_id=? AND NOT EXISTS (SELECT 1 FROM custom_course_progress p WHERE p.topic_id=t.id AND p.status='completed')", (course_id,)):
                return
    finally:
        _running.discard(course_id)


@router.get("/settings/config")
def settings_config(request: Request):
    require_admin(request)
    g=get_github_settings()
    return {
        "github": {"api_url":g.get("api_url",""),"repository":g.get("repository",""),"username":g.get("username",""),"token_configured":bool(g.get("token"))},
        "features": {
            "self_update_enabled":get_bool("self_update.enabled",False),
            "self_update_approved":get_bool("self_update.approved",False),
            "self_update_health_url":str(get_setting("self_update.health_url","")),
            "self_repair_enabled":get_bool("self_repair.enabled",True),
            "self_repair_require_approval":get_bool("self_repair.require_approval",True),
            "learning_fast_enabled":get_bool("learning.fast_enabled",False),
            "learning_interval_seconds":get_int("learning.interval_seconds",3600),
            "learning_max_retries":get_int("learning.max_retries",5),
        },
        "resources": {
            "cpu_percent": float(get_setting("resources.cpu_percent", "70")),
            "cpu_threads": get_int("resources.cpu_threads", 8),
            "ram_percent": float(get_setting("resources.ram_percent", "80")),
            "gpu_layers": get_int("resources.gpu_layers", 0),
        },
        "logging": {"level": str(get_setting("logging.level", "WARNING")).upper()},
        "image": {
            "enabled": get_bool("image.enabled", True),
            "provider": str(get_setting("image.provider", "automatic1111")),
            "url": str(get_setting("image.url", "http://127.0.0.1:7860")),
            "model": str(get_setting("image.model", "")),
            "sampler": str(get_setting("image.sampler", "DPM++ 2M Karras")),
            "steps": get_int("image.steps", 32),
            "cfg": float(get_setting("image.cfg", "7")),
            "hires": get_bool("image.hires", True),
            "hires_scale": float(get_setting("image.hires_scale", "1.5")),
            "denoise": float(get_setting("image.denoise", "0.35")),
            "hr_upscaler": str(get_setting("image.hr_upscaler", "Latent")),
            "default_size": str(get_setting("image.default_size", "1024x1024")),
            "negative_prompt": str(get_setting("image.negative_prompt", "")),
        },
    }

@router.put("/settings/github")
def save_github_config(r: GithubConfigRequest, request: Request):
    user=require_admin(request)
    try:
        GitHubConnector.save_config(api_url=r.api_url,repository=r.repository,username=r.username)
    except ValueError as exc:
        raise HTTPException(400,str(exc)) from exc
    audit(user,"github","write","200","settings-configured")
    return {"saved":True}

@router.put("/settings/features")
def save_feature_settings(r: FeatureSettingsRequest, request: Request):
    user=require_admin(request)
    if not 60 <= r.learning_interval_seconds <= 86400:
        raise HTTPException(400,"learning_interval_seconds must be 60..86400")
    if not 1 <= r.learning_max_retries <= 20:
        raise HTTPException(400,"learning_max_retries must be 1..20")
    if r.self_update_health_url:
        from urllib.parse import urlparse
        host=urlparse(r.self_update_health_url).hostname
        if host not in {"127.0.0.1","localhost","::1"}:
            raise HTTPException(400,"Self-update health URL must target the local host.")
    values={"self_update.enabled":r.self_update_enabled,"self_update.approved":r.self_update_approved,"self_update.health_url":r.self_update_health_url.strip(),"self_repair.enabled":r.self_repair_enabled,"self_repair.require_approval":r.self_repair_require_approval,"learning.fast_enabled":r.learning_fast_enabled,"learning.interval_seconds":r.learning_interval_seconds,"learning.max_retries":r.learning_max_retries}
    for key,value in values.items(): set_setting(key,value)
    audit(user,"settings","write","200","feature-settings-updated")
    return {"saved":True,"features":values}

@router.put("/settings/logging")
def save_logging_settings(r: LogSettingsRequest, request: Request):
    user = require_admin(request)
    level = r.level.strip().upper()
    allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if level not in allowed:
        raise HTTPException(400, "logging level must be DEBUG, INFO, WARNING, ERROR or CRITICAL")
    set_setting("logging.level", level)
    from .observability import configure_logging
    configure_logging()
    audit(user, "settings", "write", "200", f"logging-level:{level}")
    return {"saved": True, "logging": {"level": level}}

@router.put("/settings/image")
def save_image_settings(r: ImageSettingsRequest, request: Request):
    user = require_admin(request)
    if r.provider.strip().lower() != "automatic1111":
        raise HTTPException(400, "فقط Automatic1111 محلی پشتیبانی می‌شود.")
    url = r.url.strip().rstrip("/")
    if not url.startswith(("http://127.0.0.1:", "http://localhost:", "http://[::1]:")):
        raise HTTPException(400, "برای حالت آفلاین، آدرس موتور تصویر باید localhost باشد.")
    if not 1 <= r.steps <= 150 or not 1 <= r.cfg <= 30 or not 1 <= r.hires_scale <= 2 or not 0.1 <= r.denoise <= 1:
        raise HTTPException(400, "مقادیر کیفیت تصویر خارج از محدوده مجاز هستند.")
    if not re.fullmatch(r"\d{3,4}x\d{3,4}", r.default_size.strip()):
        raise HTTPException(400, "default_size باید مثل 1024x1024 باشد.")
    values = {
        "image.enabled": bool(r.enabled), "image.provider": "automatic1111", "image.url": url,
        "image.model": r.model.strip(), "image.sampler": r.sampler.strip() or "DPM++ 2M Karras",
        "image.steps": r.steps, "image.cfg": r.cfg, "image.hires": bool(r.hires),
        "image.hires_scale": r.hires_scale, "image.denoise": r.denoise,
        "image.hr_upscaler": r.hr_upscaler.strip() or "Latent", "image.default_size": r.default_size.strip(),
        "image.negative_prompt": r.negative_prompt.strip(),
    }
    for key, value in values.items(): set_setting(key, value)
    audit(user, "image-generation", "write", "200", "offline-image-settings-updated")
    return {"saved": True, "image": values}

@router.get("/settings/image/status")
def image_settings_status(request: Request):
    require_admin(request)
    try:
        from .image_generation import local_image_status
        return local_image_status()
    except Exception as exc:
        return {"connected": False, "error": str(exc)}

@router.put("/settings/resources")
def save_resource_settings(r: ResourceSettingsRequest, request: Request):
    user = require_admin(request)
    if not 1 <= r.cpu_percent <= 100:
        raise HTTPException(400, "cpu_percent must be 1..100")
    if not 1 <= r.cpu_threads <= 128:
        raise HTTPException(400, "cpu_threads must be 1..128")
    if not 1 <= r.ram_percent <= 100:
        raise HTTPException(400, "ram_percent must be 1..100")
    if not 0 <= r.gpu_layers <= 128:
        raise HTTPException(400, "gpu_layers must be 0..128")
    set_setting("resources.cpu_percent", round(r.cpu_percent, 2))
    set_setting("resources.cpu_threads", r.cpu_threads)
    set_setting("resources.ram_percent", round(r.ram_percent, 2))
    set_setting("resources.gpu_layers", r.gpu_layers)
    audit(user, "settings", "write", "200", "resource-settings-updated")
    return {"saved": True, "resources": {"cpu_percent": r.cpu_percent, "cpu_threads": r.cpu_threads, "ram_percent": r.ram_percent, "gpu_layers": r.gpu_layers}}

@router.get("/settings/users")
def settings_users(request: Request):
    require_admin(request)
    return {"items": fetch_all("SELECT id,username,display_name,role,active,created_at FROM users ORDER BY id")}

@router.get("/settings/tool-permissions")
def settings_tool_permissions(request: Request):
    require_admin(request)
    return {"items":fetch_all("SELECT * FROM tool_permissions ORDER BY user_id,tool_name,action")}

@router.put("/settings/tool-permissions")
def save_tool_permission(r: ToolPermissionRequest, request: Request):
    user=require_admin(request)
    if not fetch_all("SELECT id FROM users WHERE id=?",(r.user_id,)):
        raise HTTPException(404,"User not found.")
    execute("""INSERT INTO tool_permissions(user_id,tool_name,action,allowed) VALUES(?,?,?,?)
              ON CONFLICT(user_id,tool_name,action) DO UPDATE SET allowed=excluded.allowed,updated_at=CURRENT_TIMESTAMP""",(r.user_id,r.tool_name,r.action,1 if r.allowed else 0))
    audit(user,"tool-permissions","write","200",f"{r.user_id}:{r.tool_name}:{r.action}:{r.allowed}")
    return {"ok":True}

@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):
    require_admin(request)
    return HTMLResponse(SETTINGS_HTML)

@router.get("/settings/script.js")
def settings_script(request: Request):
    require_admin(request)
    script_path = Path(__file__).with_name("settings_script.js")
    if script_path.is_file():
        return Response(script_path.read_text(encoding="utf-8"), media_type="application/javascript", headers={"Cache-Control":"no-store"})
    return Response(SETTINGS_JS, media_type="application/javascript", headers={"Cache-Control":"no-store"})

@router.get("/learning", response_class=HTMLResponse)
def learning_page(request: Request):
    require_user(request)
    return HTMLResponse(LEARNING_HTML, headers={"Cache-Control":"no-store", "Pragma":"no-cache"})

@router.get("/settings/courses")
def courses(request: Request):
    require_admin(request)
    _setup()
    out=[]
    for c in fetch_all("SELECT * FROM custom_courses ORDER BY id"):
        s=_summary(int(c["id"])); c.update({"progress_percent":s["progress_percent"],"completed_topics":s["completed_topics"],"total_topics":s["total_topics"],"current":s["current"],"topics":s["topics"]}); out.append(c)
    return {"items":out}

@router.post("/settings/courses")
def create_course(r: CourseRequest, request: Request):
    user=require_admin(request); _setup()
    name=r.name.strip()
    if not name: raise HTTPException(400,"Course name is required.")
    try: cid=execute("INSERT INTO custom_courses(name,description) VALUES(?,?)",(name,r.description.strip()))
    except Exception as exc: raise HTTPException(400,"Course name already exists.") from exc
    for order,item in enumerate(r.topics,1):
        title=str(item.get("title","")).strip(); goal=str(item.get("goal","")).strip(); source=(str(item.get("source_url","")).strip() or None)
        if not title: raise HTTPException(400,"Every course topic needs a title.")
        tid=execute("INSERT INTO custom_course_topics(course_id,topic_order,title,goal,source_url) VALUES(?,?,?,?,?)",(cid,order,title,goal,source))
        execute("INSERT INTO custom_course_progress(course_id,topic_id) VALUES(?,?)",(cid,tid))
    audit(user,"learning","write","200",f"course-created:{cid}")
    return {"id":cid,"status":"created"}

@router.put("/settings/courses/{course_id}")
def update_course(course_id: int, r: CourseUpdateRequest, request: Request):
    user = require_admin(request); _setup()
    if not _course(course_id):
        raise HTTPException(404, "Course not found.")
    name = r.name.strip()
    if not name:
        raise HTTPException(400, "Course name is required.")
    try:
        execute("UPDATE custom_courses SET name=?, description=? WHERE id=?", (name, r.description.strip(), course_id))
    except Exception as exc:
        raise HTTPException(400, "Course name already exists.") from exc
    _ensure_custom_review_schedule(course_id)
    audit(user, "learning", "write", "200", f"course-updated:{course_id}")
    return {"status": "updated", "course_id": course_id}

@router.put("/settings/courses/{course_id}/topics/{topic_id}")
def update_course_topic(course_id: int, topic_id: int, r: CourseTopicRequest, request: Request):
    user = require_admin(request); _setup()
    rows = fetch_all("SELECT id FROM custom_course_topics WHERE id=? AND course_id=?", (topic_id, course_id))
    if not rows:
        raise HTTPException(404, "Topic not found.")
    title = r.title.strip()
    if not title:
        raise HTTPException(400, "Topic title is required.")
    execute(
        "UPDATE custom_course_topics SET title=?, goal=?, source_url=? WHERE id=? AND course_id=?",
        (title, r.goal.strip(), r.source_url.strip() or None, topic_id, course_id),
    )
    _ensure_custom_review_schedule(course_id)
    audit(user, "learning", "write", "200", f"course-topic-updated:{course_id}:{topic_id}")
    return {"status": "updated", "topic_id": topic_id}

@router.post("/settings/courses/{course_id}/topics")
def add_course_topic(course_id: int, r: CourseTopicRequest, request: Request):
    user = require_admin(request); _setup()
    if not _course(course_id):
        raise HTTPException(404, "Course not found.")
    title = r.title.strip()
    goal = r.goal.strip()
    source = r.source_url.strip() or None
    rows = fetch_all("SELECT COALESCE(MAX(topic_order),0) AS n FROM custom_course_topics WHERE course_id=?", (course_id,))
    order = int(rows[0]["n"] or 0) + 1
    try:
        tid = execute(
            "INSERT INTO custom_course_topics(course_id,topic_order,title,goal,source_url) VALUES(?,?,?,?,?)",
            (course_id, order, title, goal, source),
        )
        execute("INSERT INTO custom_course_progress(course_id,topic_id) VALUES(?,?)", (course_id, tid))
    except Exception as exc:
        raise HTTPException(400, "Unable to add topic.") from exc
    _ensure_custom_review_schedule(course_id)
    audit(user, "learning", "write", "200", f"course-topic-added:{course_id}:{tid}")
    return {"id": tid, "course_id": course_id, "topic_order": order, "status": "planned"}

@router.get("/settings/courses/{course_id}/progress")
def course_progress(course_id:int,request:Request):
    require_user(request); _setup()
    if not _course(course_id): raise HTTPException(404,"Course not found.")
    return _summary(course_id)

@router.post("/settings/courses/{course_id}/start")
def course_start(course_id:int,request:Request):
    user=require_user(request); _setup()
    if not _course(course_id): raise HTTPException(404,"Course not found.")
    _ensure_custom_review_schedule(course_id)
    if course_id not in _running:
        _workers.submit(_run_course,course_id)
    audit(user,"learning","execute","202",f"course-start:{course_id}")
    return {"status":"started","course_id":course_id}

@router.post("/learning/{course_id}/pause")
def learning_pause(course_id:int,request:Request):
    user=require_user(request); _setup()
    if not _course(course_id): raise HTTPException(404,"Course not found.")
    execute("UPDATE custom_course_progress SET status='paused',phase='paused',updated_at=CURRENT_TIMESTAMP WHERE course_id=? AND status='started'",(course_id,))
    audit(user,"learning","write","200",f"course-pause:{course_id}")
    return {"status":"paused","course_id":course_id}

@router.post("/settings/courses/{course_id}/pause")
def course_pause(course_id:int,request:Request):
    user=require_admin(request); _setup()
    execute("UPDATE custom_course_progress SET status='paused',phase='paused',updated_at=CURRENT_TIMESTAMP WHERE course_id=? AND status='started'",(course_id,))
    audit(user,"learning","write","200",f"course-pause:{course_id}")
    return {"status":"paused","course_id":course_id}

@router.post("/settings/github-token")
def github_token(r:TokenRequest,request:Request):
    user=require_admin(request)
    token=r.token.strip()
    if token and len(token)<20: raise HTTPException(400,"GitHub token is too short.")
    try:
        if not token:
            GitHubConnector.save_token("")
            return {"saved":False,"authenticated":False}
        GitHubConnector.save_token(token)
        identity=GitHubConnector(token=token).whoami()
        audit(user,"github","write","200",f"token-saved:{identity.get('login','unknown')}")
        return {"saved":True,"authenticated":True,"login":identity.get("login"),"name":identity.get("name")}
    except Exception as exc:
        GitHubConnector.save_token("")
        raise HTTPException(502,f"GitHub token verification failed: {exc}") from exc

@router.get("/settings/github")
def github_settings(request:Request):
    require_admin(request)
    try:
        return {"connection":GitHubConnector().whoami(),"token_source":GitHubConnector.token_source()}
    except Exception as exc:
        return {"connection":None,"token_source":GitHubConnector.token_source(),"error":str(exc)}

@router.get("/learning/active")
def learning_active(request:Request):
    require_user(request); _setup()
    items=[]
    for c in fetch_all("SELECT * FROM custom_courses WHERE active=1 ORDER BY id"):
        summary=_summary(int(c["id"]))
        review = fetch_all("SELECT next_review_at FROM learning_domains WHERE name=? LIMIT 1", (f"custom_course:{int(c['id'])}",))
        items.append({
            "course": c,
            "summary": summary,
            "active": summary["completed_topics"] < summary["total_topics"],
            "next_review_at": review[0]["next_review_at"] if review else None,
        })
    return {"items":items,"running":sorted(_running)}

@router.get("/learning/catalog")
def learning_catalog(request:Request):
    require_user(request); _setup()
    return {"items":fetch_all("SELECT * FROM custom_courses WHERE active=1 ORDER BY id")}

@router.post("/learning/{course_id}/start")
def learning_start_public(course_id:int,request:Request):
    return course_start(course_id,request)

SETTINGS_JS = '''function byId(id){return document.getElementById(id)}
async function req(url,opt){var r;try{r=await fetch(url,opt||{});}catch(e){throw Error('ارتباط با سرور برقرار نشد: '+(e&&e.message?e.message:'Failed to fetch'))}var text=await r.text();if(!r.ok){var msg=text;try{var e=JSON.parse(text);msg=e.detail||e.message||text}catch(_){ }throw Error(msg||('HTTP '+r.status))}try{return JSON.parse(text)}catch(e){throw Error('پاسخ نامعتبر از سرور: '+text.slice(0,500))}}
function esc(v){return String(v==null?'':v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}
function setText(id,value){var e=byId(id);if(e)e.textContent=value}
async function loadUsers(){var box=byId('users');if(!box)return;box.textContent='در حال بارگذاری...';try{var j=await req('/settings/users');var items=j.items||[];box.innerHTML=items.map(function(u){return '<div class="topic"><b>'+esc(u.username)+'</b> — '+esc(u.display_name||'بدون نام')+' — نقش: '+esc(u.role)+' — '+(u.active?'فعال':'غیرفعال')+(u.role==='admin'?'':' <button type="button" onclick="toggleUser('+u.id+','+(!u.active)+')">'+(u.active?'غیرفعال‌کردن':'فعال‌کردن')+'</button>')+'</div>'}).join('')||'کاربری ثبت نشده است'}catch(e){box.textContent='خطا در بارگذاری کاربران: '+e.message}}
async function toggleUser(id,active){try{await req('/admin/users/'+id+'/active?active='+active,{method:'PATCH'});await loadUsers()}catch(e){setText('userout',e.message)}}
async function addUser(){try{var j=await req('/admin/users',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:byId('nu').value,password:byId('np').value,display_name:byId('nd').value,active:true})});setText('userout','کاربر ایجاد شد: '+j.user.username);byId('nu').value='';byId('np').value='';byId('nd').value='';loadUsers();loadPermissions()}catch(e){setText('userout',e.message)}}
async function loadSettings(){try{var j=await req('/settings/config');byId('apiurl').value=j.github.api_url||'';byId('repo').value=j.github.repository||'';byId('ghuser').value=j.github.username||'';byId('su_enabled').checked=!!j.features.self_update_enabled;byId('su_approved').checked=!!j.features.self_update_approved;byId('su_health').value=j.features.self_update_health_url||'';byId('sr_enabled').checked=!!j.features.self_repair_enabled;byId('sr_approval').checked=!!j.features.self_repair_require_approval;byId('lf_enabled').checked=!!j.features.learning_fast_enabled;byId('lf_interval').value=j.features.learning_interval_seconds;byId('lf_retries').value=j.features.learning_max_retries;byId('cpu_percent').value=j.resources.cpu_percent;byId('cpu_threads').value=j.resources.cpu_threads;byId('ram_percent').value=j.resources.ram_percent;byId('gpu_layers').value=j.resources.gpu_layers;setText('gitout',j.github.token_configured?'Token تنظیم شده است':'Token تنظیم نشده است');setText('resourceout','مقادیر فعال: CPU '+j.resources.cpu_percent+'% · '+j.resources.cpu_threads+' thread · RAM '+j.resources.ram_percent+'% · GPU '+j.resources.gpu_layers+' layer')}catch(e){setText('gitout','خطا در بارگذاری تنظیمات: '+e.message)}}
async function saveGithubConfig(){try{await req('/settings/github',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({api_url:byId('apiurl').value.trim(),repository:byId('repo').value.trim(),username:byId('ghuser').value.trim()})});setText('gitout','تنظیمات GitHub ذخیره شد')}catch(e){setText('gitout',e.message)}}
async function saveToken(){try{var j=await req('/settings/github-token',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:byId('token').value})});setText('gitout',j.authenticated?'Token معتبر و متصل به @'+j.login:'Token حذف شد');byId('token').value='';loadSettings()}catch(e){setText('gitout',e.message)}}
async function checkGit(){try{var j=await req('/git/check');setText('gitout',j.message||j.status||'بررسی انجام شد')}catch(e){setText('gitout','خطا در بررسی اتصال: '+e.message)}}
async function saveFeatures(){try{await req('/settings/features',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({self_update_enabled:byId('su_enabled').checked,self_update_approved:byId('su_approved').checked,self_update_health_url:byId('su_health').value,self_repair_enabled:byId('sr_enabled').checked,self_repair_require_approval:byId('sr_approval').checked,learning_fast_enabled:byId('lf_enabled').checked,learning_interval_seconds:Number(byId('lf_interval').value||3600),learning_max_retries:Number(byId('lf_retries').value||5)})});setText('suout','تنظیمات ذخیره شد');setText('srout','تنظیمات ذخیره شد');setText('lfout','تنظیمات ذخیره شد');loadSettings()}catch(e){setText('suout',e.message);setText('srout',e.message);setText('lfout',e.message)}}
window.saveResources=async function saveResources(){try{var payload={cpu_percent:Number(byId('cpu_percent').value||70),cpu_threads:Number(byId('cpu_threads').value||8),ram_percent:Number(byId('ram_percent').value||80),gpu_layers:Number(byId('gpu_layers').value||0)};var j=await req('/settings/resources',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});byId('cpu_percent').value=j.resources.cpu_percent;byId('cpu_threads').value=j.resources.cpu_threads;byId('ram_percent').value=j.resources.ram_percent;byId('gpu_layers').value=j.resources.gpu_layers;setText('resourceout','مقادیر فعال: CPU '+j.resources.cpu_percent+'% · '+j.resources.cpu_threads+' thread · RAM '+j.resources.ram_percent+'% · GPU '+j.resources.gpu_layers+' layer')}catch(e){setText('resourceout','خطا در ذخیره منابع: '+e.message)}}
var PERM_TOOLS=['chat','code-generation','code-execution','learning','scheduler','github','security','database','voice','models','memory','web','projects','eval','self-update','self-repair','help','tools','files'];
function permissionCell(uid,tool,action,allowed){return '<label style="display:inline-block;margin:3px"><input type="checkbox" '+(allowed?'checked':'')+' onchange="setPermission('+uid+',\''+tool+'\',\''+action+'\',this.checked)"> '+tool+':'+action+'</label>'}
async function loadPermissions(){var box=byId('permissions');if(!box)return;box.textContent='در حال بارگذاری...';try{var pair=await Promise.all([req('/settings/users'),req('/settings/tool-permissions')]);var usersList=pair[0].items||[];var items=pair[1].items||[];var map={};items.forEach(function(x){map[x.user_id+':'+x.tool_name+':'+x.action]=!!x.allowed});box.innerHTML=usersList.map(function(user){var html='<div class="topic"><b>'+esc(user.username)+'</b> — '+esc(user.role)+'<div>';PERM_TOOLS.forEach(function(tool){['read','write','execute'].forEach(function(action){html+=permissionCell(user.id,tool,action,!!map[user.id+':'+tool+':'+action])})});return html+'</div></div>'}).join('')||'کاربری ثبت نشده است'}catch(e){box.textContent='خطا در بارگذاری مجوزها: '+e.message}}
async function setPermission(uid,tool,action,allowed){try{await req('/settings/tool-permissions',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:uid,tool_name:tool,action:action,allowed:allowed})})}catch(e){alert('خطا در ذخیره مجوز: '+e.message);loadPermissions()}}
async function loginGit(){try{var j=await req('/git/login',{method:'POST'});setText('gitout',j.message||'درخواست ورود ارسال شد')}catch(e){setText('gitout',e.message)}}
async function logoutGit(){try{var j=await req('/git/logout',{method:'POST'});setText('gitout',j.message||'خروج انجام شد');loadSettings()}catch(e){setText('gitout',e.message)}}
async function createCourse(){try{var lines=byId('ct').value.split(/\n+/).map(function(x){return x.trim()}).filter(Boolean);var topics=lines.map(function(x){var p=x.split('|').map(function(v){return v.trim()});return {title:p[0],goal:p[1]||'',source_url:p[2]||''}});var j=await req('/settings/courses',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:byId('cn').value,description:byId('cd').value,topics:topics})});setText('newcourseout','آموزش ساخته شد: '+j.id);loadCourses()}catch(e){setText('courseout',e.message)}}
async function startCourse(id){try{await req('/settings/courses/'+id+'/start',{method:'POST'});loadCourses()}catch(e){setText('courseout',e.message)}}
async function addCourseTopic(){try{var id=Number(byId('existing_course_id').value);var p={title:byId('existing_topic').value,goal:byId('existing_goal').value,source_url:byId('existing_source').value};await req('/settings/courses/'+id+'/topics',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});setText('courseout','Topic جدید اضافه شد و برای یادگیری برنامه‌ریزی شد.');loadCourses()}catch(e){setText('courseout',e.message)}}
async function loadCourses(){var box=byId('courses');if(!box)return;try{var j=await req('/settings/courses');box.innerHTML=(j.items||[]).map(function(c){var topics=(c.topics||[]).map(function(t){return '<div class="topic"><div><b>'+esc(t.topic_order)+'.</b> <input id="ctitle'+t.id+'" value="'+esc(t.title)+'"><input id="csource'+t.id+'" value="'+esc(t.source_url||'')+'" placeholder="لینک منبع رسمی"><textarea id="cgoal'+t.id+'" rows="2" placeholder="توضیحات / هدف درس">'+esc(t.goal||'')+'</textarea>'+(t.lesson?'<details><summary>متن کامل درس فعلی</summary><pre style="white-space:pre-wrap;max-height:420px;overflow:auto">'+esc(t.lesson)+'</pre></details>':'<div class="muted">متن درس هنوز تولید نشده است.</div>')+'<button type="button" onclick="saveTopic('+c.id+','+t.id+')">ذخیره مبحث</button></div>'}).join('');return '<div class="card"><h3>آموزش #'+c.id+'</h3><input id="cname'+c.id+'" value="'+esc(c.name)+'"><textarea id="cdesc'+c.id+'" rows="2">'+esc(c.description||'')+'</textarea><div class="bar"><div class="fill" style="width:'+c.progress_percent+'%">'+c.progress_percent+'%</div></div><p class="muted">'+c.completed_topics+' از '+c.total_topics+' سرفصل کامل شده'+(c.current?' · اکنون: '+esc(c.current.title)+' · مرحله: '+esc(c.current.phase):'')+'</p><button type="button" onclick="saveCourse('+c.id+')">ذخیره نام و توضیحات آموزش</button>'+topics+'</div>'}).join('')||'آموزشی نیست'}catch(e){box.textContent='خطا در بارگذاری آموزش‌ها: '+e.message}}
async function saveCourse(id){try{await req('/settings/courses/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:byId('cname'+id).value,description:byId('cdesc'+id).value})});await loadCourses()}catch(e){setText('courseout',e.message)}}
async function saveTopic(courseId,topicId){try{await req('/settings/courses/'+courseId+'/topics/'+topicId,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:byId('ctitle'+topicId).value,goal:byId('cgoal'+topicId).value,source_url:byId('csource'+topicId).value})});await loadCourses()}catch(e){setText('courseout',e.message)}}
loadSettings();loadUsers();loadPermissions();loadCourses();setInterval(loadCourses,10000)'''

SETTINGS_HTML = """<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>تنظیمات | My-AI</title><style>body{font-family:Tahoma,system-ui;background:#f3f4f6;margin:0;color:#17202a}.wrap{max-width:1100px;margin:auto;padding:20px}.card{background:#fff;padding:18px;border-radius:14px;margin:12px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}input,textarea,select{width:100%;box-sizing:border-box;padding:10px;margin:5px 0;border:1px solid #ccc;border-radius:8px}button{padding:9px 14px;margin:3px;border:0;border-radius:8px;cursor:pointer}.bar{height:22px;background:#ddd;border-radius:8px;overflow:hidden}.fill{height:100%;background:#2563eb;color:#fff;text-align:center;line-height:22px;font-size:12px}.topic{border:1px solid #ddd;padding:9px;border-radius:9px;margin:6px 0}.muted{font-size:13px;color:#667085}.ok{background:#dcfce7}.warn{background:#fef3c7}.danger{background:#fee2e2}</style><style>body{background:linear-gradient(135deg,#eef2ff,#f8fafc 45%,#ecfeff)!important}.wrap{max-width:1180px!important}.card{border:1px solid #e5e7eb;box-shadow:0 8px 24px #0f172a0b!important;transition:.18s}.card:hover{box-shadow:0 12px 30px #0f172a12!important}.wrap>h1{background:linear-gradient(135deg,#111827,#1e3a8a);color:#fff;padding:24px;border-radius:20px}.grid{gap:16px!important}button{background:#1d4ed8;color:#fff!important;font-weight:700}button:hover{filter:brightness(1.05)}.topic{background:#f8fafc;border-color:#e2e8f0}.permissionGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px}.permGroup{background:#f8fafc;padding:10px;border-radius:10px;border:1px solid #e2e8f0}@media(max-width:700px){.wrap{padding:12px!important}}</style><div class='wrap'><form id='settings-form' hidden></form><h1>تنظیمات My-AI</h1><p><a href='/'>صفحه اصلی</a> · <a href='/learning'>پیشرفت و مسیر یادگیری</a></p><div class='grid'><section class='card'><h2>اتصال GitHub</h2><p class='muted'>هیچ Repository یا API URL پیش‌فرضی وجود ندارد. تنظیمات در دیتابیس نگهداری می‌شود؛ Token به‌صورت رمزنگاری‌شده ذخیره می‌شود. GitHub REST API با username/password احراز هویت نمی‌کند و برای API باید Token یا OAuth/CLI استفاده شود.</p><input id='apiurl' placeholder='GitHub API URL'><input id='repo' placeholder='owner/repository'><input id='ghuser' placeholder='GitHub username (اختیاری)'><input id='token' type='password' form='settings-form' autocomplete='new-password' placeholder='Personal Access Token'><button onclick='saveGithubConfig()'>ثبت تنظیمات GitHub</button><button onclick='saveToken()'>ثبت Token</button><button onclick='checkGit()'>بررسی اتصال</button><button onclick='loginGit()'>ورود با GitHub CLI/OAuth</button><button onclick='logoutGit()'>خروج</button><div id='gitout' class='muted'></div></section>
<section class='card'><h2>Self-Update</h2><label><input id='su_enabled' type='checkbox'> فعال‌سازی Self-Update برای بررسی و اجرای به‌روزرسانی خودکار</label><label><input id='su_approved' type='checkbox'> اجازه اجرای Update بدون تأیید دستی در مرحله اجرا</label><input id='su_health' placeholder='Health URL محلی، مثلاً http://127.0.0.1:8000/health'><button onclick='saveFeatures()'>ذخیره</button><div id='suout' class='muted'></div></section>
<section class='card'><h2>Self-Repair</h2><label><input id='sr_enabled' type='checkbox'> فعال‌سازی Self-Repair برای پیشنهاد/اجرای تعمیرات</label><label><input id='sr_approval' type='checkbox' checked> قبل از اعمال تعمیر، تأیید ادمین الزامی باشد</label><button onclick='saveFeatures()'>ذخیره</button><div id='srout' class='muted'></div></section>
<section class='card'><h2>یادگیری سریع</h2><label><input id='lf_enabled' type='checkbox'> فعال</label><input id='lf_interval' type='number' min='60' max='86400' placeholder='فاصله یادگیری (ثانیه)'><input id='lf_retries' type='number' min='1' max='20' placeholder='حداکثر تلاش منبع'><button onclick='saveFeatures()'>ذخیره</button><div id='lfout' class='muted'></div></section><section class='card'><h2>تولید تصویر کاملاً آفلاین</h2><p class='muted'>فقط Automatic1111 روی همین کامپیوتر استفاده می‌شود و این مسیر هیچ API ابری ندارد. برای کیفیت بالا، checkpoint مناسب Manga/Anime/SDXL را در Automatic1111 نصب کنید.</p><label><input id='img_enabled' type='checkbox'> فعال</label><input id='img_url' placeholder='http://127.0.0.1:7860'><input id='img_model' placeholder='نام checkpoint/مدل نصب‌شده'><input id='img_sampler' placeholder='DPM++ 2M Karras'><div class='grid'><label>Steps<input id='img_steps' type='number' min='1' max='150'></label><label>CFG<input id='img_cfg' type='number' min='1' max='30' step='0.1'></label><label>اندازه<input id='img_size' placeholder='1024x1024'></label><label>Hires Scale<input id='img_hires_scale' type='number' min='1' max='2' step='0.1'></label><label>Denoise<input id='img_denoise' type='number' min='0.1' max='1' step='0.05'></label><input id='img_upscaler' placeholder='Latent'></div><label><input id='img_hires' type='checkbox'> Hires Fix</label><textarea id='img_negative' rows='5' placeholder='Negative prompt پیش‌فرض'></textarea><button onclick='saveImageSettings()'>ذخیره تنظیمات تصویر</button><button onclick='checkImageEngine()'>بررسی موتور محلی</button><div id='imgout' class='muted'></div></section><section class='card'><h2>لاگ‌های کنسول</h2><p class='muted'>حداقل سطح لاگ‌هایی که در کنسول نمایش داده می‌شوند را انتخاب کنید. تغییر این گزینه بدون ری‌استارت اعمال می‌شود.</p><select id='log_level'><option value='DEBUG'>Debug — همه جزئیات</option><option value='INFO'>Info — اطلاعات و هشدارها</option><option value='WARNING'>Warning — هشدار و خطا</option><option value='ERROR'>Error — فقط خطاها</option><option value='CRITICAL'>Critical — فقط خطاهای بحرانی</option></select><button onclick='saveLogging()'>ذخیره تنظیمات لاگ</button><div id='logout' class='muted'></div></section><section class='card'><h2>منابع سخت‌افزاری</h2><p class='muted'>سقف پیش‌فرض اجرای یادگیری: CPU برابر 70٪ با 8 thread، RAM برابر 80٪ و GPU برابر 0 لایه (فقط CPU). این مقادیر قابل تغییر هستند.</p><label>حداکثر CPU (%)<input id='cpu_percent' type='number' min='1' max='100' step='0.5'></label><label>تعداد CPU thread<input id='cpu_threads' type='number' min='1' max='128' step='1'></label><label>حداکثر RAM (%)<input id='ram_percent' type='number' min='1' max='100' step='0.5'></label><label>GPU layers (0 = فقط CPU)<input id='gpu_layers' type='number' min='0' max='128' step='1'></label><button onclick='saveResources()'>ذخیره منابع</button><div id='resourceout' class='muted'></div></section><section class='card'><h2>مدیریت کاربران</h2><div id='users'>در حال بارگذاری...</div><hr><input id='nu' autocomplete='username' placeholder='نام کاربری'><input id='np' type='password' form='settings-form' autocomplete='new-password' placeholder='رمز عبور حداقل ۱۰ کاراکتر'><input id='nd' placeholder='نام نمایشی'><button onclick='addUser()'>ایجاد کاربر</button><div id='userout' class='muted'></div></section></div>
<section class='card'><h2>مجوز ابزار کاربران</h2><p class='muted'>برای هر کاربر، ابزار و نوع عملیات را مشخص کنید. عدم وجود مجوز یعنی Deny.</p><div id='permissions'>در حال بارگذاری...</div></section><section class='card'><h2>افزودن Topic به آموزش موجود</h2><p class='muted'>Topic جدید با وضعیت «برنامه‌ریزی‌شده» اضافه می‌شود و درصد کلی آموزش دوباره محاسبه خواهد شد.</p><input id='existing_course_id' type='number' min='1' placeholder='شناسه آموزش'><input id='existing_topic' placeholder='عنوان Topic جدید'><input id='existing_goal' placeholder='هدف Topic'><input id='existing_source' placeholder='آدرس منبع رسمی اختیاری'><button onclick='addCourseTopic()'>افزودن Topic</button><div id='courseout' class='muted'></div></section><section class='card'><h2>ساخت آموزش جدید</h2><p class='muted'>هر خط یک سرفصل: <code>عنوان | هدف | آدرس منبع رسمی اختیاری</code>. می‌توانی هر موضوع دلخواهی بسازی.</p><input id='cn' placeholder='نام آموزش، مثلاً Python'><input id='cd' placeholder='توضیح آموزش'><textarea id='ct' rows='12' placeholder='Python functions | توابع و پارامترها | https://docs.python.org/3/tutorial/'></textarea><button onclick='createCourse()'>ایجاد آموزش</button><div id='newcourseout' class='muted'></div></section></div><script src='/settings/script.js?v=20260923-3'></script><script>
(function(){
async function imageSettingsLoad(){
  try{var j=await req("/settings/config");var x=j.image||{};byId("img_enabled").checked=!!x.enabled;byId("img_url").value=x.url||"";byId("img_model").value=x.model||"";byId("img_sampler").value=x.sampler||"";byId("img_steps").value=x.steps||32;byId("img_cfg").value=x.cfg||7;byId("img_hires").checked=!!x.hires;byId("img_hires_scale").value=x.hires_scale||1.5;byId("img_denoise").value=x.denoise||0.35;byId("img_upscaler").value=x.hr_upscaler||"Latent";byId("img_size").value=x.default_size||"1024x1024";byId("img_negative").value=x.negative_prompt||"";}catch(e){setText("imgout","خطا در بارگذاری تنظیمات تصویر: "+e.message)}
}
window.saveImageSettings=async function(){
 try{var p={enabled:byId("img_enabled").checked,provider:"automatic1111",url:byId("img_url").value.trim(),model:byId("img_model").value.trim(),sampler:byId("img_sampler").value.trim(),steps:Number(byId("img_steps").value||32),cfg:Number(byId("img_cfg").value||7),hires:byId("img_hires").checked,hires_scale:Number(byId("img_hires_scale").value||1.5),denoise:Number(byId("img_denoise").value||0.35),hr_upscaler:byId("img_upscaler").value.trim(),default_size:byId("img_size").value.trim()||"1024x1024",negative_prompt:byId("img_negative").value};await req("/settings/image",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(p)});setText("imgout","تنظیمات تصویر آفلاین ذخیره شد.");await imageSettingsLoad()}catch(e){setText("imgout","خطا: "+e.message)}
};
window.checkImageEngine=async function(){try{var j=await req("/settings/image/status");setText("imgout",j.connected?"اتصال برقرار است · مدل فعال: "+(j.model||"نامشخص")+" · مدل‌های نصب‌شده: "+((j.models||[]).length):"موتور محلی در دسترس نیست: "+(j.error||"خطای نامشخص"))}catch(e){setText("imgout","خطا در بررسی موتور: "+e.message)}};
imageSettingsLoad();
})();
</script></html>"""

LEARNING_HTML = """<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>پیشرفت یادگیری | My-AI</title><style>body{font-family:Tahoma,system-ui;background:linear-gradient(135deg,#eef2ff,#f8fafc 45%,#ecfeff);margin:0;color:#17202a}.wrap{max-width:1180px;margin:auto;padding:20px}.card{background:rgba(255,255,255,.92);padding:18px;border-radius:16px;margin:12px 0;border:1px solid #e5e7eb;box-shadow:0 8px 24px #0f172a0b}.bar{height:26px;background:#ddd;border-radius:9px;overflow:hidden}.fill{height:100%;background:#2563eb;color:#fff;text-align:center;line-height:26px;min-width:2em}.fill.done{background:#16a34a}.completed .fill{background:#16a34a}.course{border:1px solid #d0d5dd;border-radius:12px;margin:12px 0;overflow:hidden;background:#fff}.course>summary{cursor:pointer;padding:16px;font-size:18px;font-weight:700;list-style:none}.course>summary::-webkit-details-marker{display:none}.courseBody{padding:0 16px 16px}.topic{padding:12px;border:1px solid #e4e7ec;border-radius:10px;margin:8px 0}.topicHead{display:flex;justify-content:space-between;gap:12px;align-items:center}.started{background:#eff6ff}.completed{background:#ecfdf3;border-color:#22c55e}.course.complete{border-color:#22c55e;background:#f0fdf4}.course.complete>summary{color:#166534}.paused{background:#fffaeb}.small{font-size:13px;color:#667085}pre{direction:ltr;text-align:left}.empty{padding:20px;text-align:center;color:#667085}</style><div class='wrap'><h1>پیشرفت یادگیری</h1><p><a href='/settings'>تنظیمات</a> · <a href='/'>صفحه اصلی</a></p><p class='small'>همه مباحث موجود اینجا هستند. روی هر مبحث کلیک کنید تا سرفصل‌ها و درصد یادگیری هر سرفصل باز شود.</p><div id='root'>در حال بارگذاری...</div></div><script>
async function req(u){let r=await fetch(u,{cache:'no-store'});let text=await r.text();if(!r.ok){let msg=text;try{let j=JSON.parse(text);msg=j.detail||j.message||text}catch(_){ }throw Error(msg||('HTTP '+r.status))}try{return JSON.parse(text)}catch(_){throw Error('پاسخ نامعتبر از سرور: '+text.slice(0,500))}}
function esc(v){return String(v==null?'':v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')}
function bar(p,done){p=Number(p||0);return '<div class="bar"><div class="fill '+(done?'done':'')+'" style="width:'+Math.max(0,Math.min(100,p))+'%">'+p+'%</div></div>'}
function topicStatus(s,p){if(Number(p||0)>=100||s==='completed')return 'تکمیل‌شده';if(s==='started')return 'در حال یادگیری';if(s==='paused')return 'متوقف‌شده';if(s==='planned')return 'برنامه‌ریزی‌شده';return s||'نامشخص'}
function parseDateValue(v){if(!v)return null;var s=String(v).trim();if(/^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$/.test(s))s=s.replace(' ','T')+'Z';else if(/^[0-9]{4}-[0-9]{2}-[0-9]{2}T/.test(s)&&!/[zZ]|[+-][0-9]{2}:[0-9]{2}$/.test(s))s+='Z';var d=new Date(s);return isNaN(d.getTime())?null:d}
function formatAttempt(v){if(!v)return 'هنوز تلاشی انجام نشده';var d=parseDateValue(v);if(!d)return esc(v);return new Intl.DateTimeFormat('fa-IR-u-ca-persian',{dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Tehran'}).format(d)}
function formatRemaining(v){if(!v)return 'زمان‌بندی هفتگی ثبت نشده';var d=parseDateValue(v);if(!d)return 'نامشخص';var ms=d.getTime()-Date.now();if(ms<=0)return 'رسیده است';var days=Math.floor(ms/86400000);ms%=86400000;var h=Math.floor(ms/3600000);ms%=3600000;var m=Math.floor(ms/60000);return (days?days+' روز و ':'')+h+' ساعت و '+m+' دقیقه'}
function topicHtml(t,language){var pct=Number(t.progress_percent||0),done=pct>=100||t.status==='completed',cls=done?'completed':t.status==='paused'?'paused':t.status==='started'?'started':'';var source=t.source_url?'<div class="small">منبع: <a href="'+esc(t.source_url)+'" target="_blank" rel="noopener noreferrer">'+esc(t.source_url)+'</a></div>':'';var lesson=t.lesson?'<div class="lesson"><pre style="white-space:pre-wrap;overflow:auto;max-height:700px">'+esc(t.lesson)+'</pre></div>':'<div class="lesson" data-language="'+esc(language)+'" data-topic="'+esc(t.topic||t.title)+'"><button type="button" onclick="loadLesson(this)">نمایش متن درس</button></div>';return '<details class="topic '+cls+'"><summary><div class="topicHead"><b>'+esc(t.order||t.topic_order)+'. '+esc(t.topic||t.title)+'</b><b>'+pct+'%</b></div>'+bar(pct,done)+'</summary><div class="small">وضعیت: '+topicStatus(t.status,pct)+' · مرحله: '+esc(t.phase||'planned')+'</div><div>هدف: '+esc(t.goal)+'</div>'+source+'<div class="small">آخرین تلاش: '+formatAttempt(t.last_attempt_at)+'</div>'+(t.score!=null?'<div class="small">امتیاز ارزیابی: '+esc(t.score)+'</div>':'')+lesson+'</details>'}
async function loadLesson(button){var box=button.parentElement,language=box.dataset.language,topic=box.dataset.topic;button.disabled=true;button.textContent='در حال دریافت درس...';try{var r=await fetch('/learning/lesson?language='+encodeURIComponent(language)+'&topic='+encodeURIComponent(topic),{cache:'no-store'});var j=await r.json();if(!r.ok)throw Error(j.detail||'خطا');box.innerHTML=j.lesson?'<pre style="white-space:pre-wrap;overflow:auto;max-height:700px">'+esc(j.lesson)+'</pre>':'<div class="small">متن درس هنوز تولید نشده است.</div>'}catch(e){button.disabled=false;button.textContent='نمایش متن درس';box.insertAdjacentHTML('beforeend','<div class="small">خطا: '+esc(e.message)+'</div>')}}
async function load(){try{var a=await req('/learning/status'),j=a.courses||[],custom=await req('/learning/active'),sched=await req('/scheduler/status'),workers=sched.workers||[],nextReviews=(sched.weekly_review&&sched.weekly_review.next_reviews)||[],reviewMap={},seen={},customMap={},html='';nextReviews.forEach(function(x){reviewMap[String(x.name||'').toLowerCase()]=x.next_review_at});(custom.items||[]).forEach(function(x){var c=x.course,s=x.summary,key=String(c.name||'').trim().toLowerCase();if(key)customMap[key]=x});Object.keys(customMap).forEach(function(key){var x=customMap[key],c=x.course,s=x.summary,done=s.total_topics>0&&s.completed_topics===s.total_topics;seen[key]=true;html+='<details class="course '+(done?'complete':'')+'"><summary>'+esc(c.name)+' — '+(done?'تکمیل‌شده · ':'')+Number(s.progress_percent||0)+'% ('+s.completed_topics+'/'+s.total_topics+')</summary><div class="courseBody">'+bar(s.progress_percent,done)+'<div class="small">مرور هفتگی بعدی: '+formatRemaining(x.next_review_at)+'</div>'+s.topics.map(function(t){return topicHtml(t,c.name)}).join('')+'</div></details>'});j.forEach(function(c){var key=String(c.language||'').trim().toLowerCase();if(!key||customMap[key])return;var done=Number(c.progress_percent||0)>=100;seen[key]=true;html+='<details class="course '+(done?'complete':'')+'"><summary>'+esc(c.language)+' — '+(done?'تکمیل‌شده · ':'')+Number(c.progress_percent||0)+'% ('+c.completed_topics+'/'+c.total_topics+')</summary><div class="courseBody">'+bar(c.progress_percent,done)+'<div class="small">مرور هفتگی بعدی: '+formatRemaining(reviewMap[key])+'</div>'+c.topics.map(function(t){return topicHtml(t,c.language)}).join('')+'</div></details>'});workers.forEach(function(w){var key=String(w.language||'').trim().toLowerCase();if(!key||key.indexOf('custom_course:')===0||seen[key]||customMap[key])return;html+='<details class="course"><summary>'+esc(w.language)+' — در حال یادگیری</summary><div class="courseBody"><div class="small">مرحله: '+esc(w.stage||w.status||'running')+' · موضوع فعلی: '+esc(w.current_topic||'در حال پردازش')+'</div></div></details>';seen[key]=true});root.innerHTML=html||'<div class="card empty">هنوز آموزشی ثبت نشده است.</div>'}catch(e){root.textContent='خطا: '+e.message}}
load();setInterval(function(){var y=window.scrollY;var states=Array.from(root.querySelectorAll('details')).map(function(d){return d.open});load().then(function(){Array.from(root.querySelectorAll('details')).forEach(function(d,i){if(i<states.length)d.open=states[i]});window.scrollTo(0,y)}).catch(function(){});},5000)
</script></html>"""
def shutdown_course_workers() -> None:
    """Stop the custom-course executor during application shutdown."""
    global _workers
    try:
        _workers.shutdown(wait=False, cancel_futures=True)
    except TypeError:
        _workers.shutdown(wait=False)
    except RuntimeError:
        pass

def start_named_course(name: str) -> int | None:
    """Start a named custom course and return its course id."""
    _setup()
    rows = fetch_all("SELECT id FROM custom_courses WHERE lower(name)=lower(?) AND active=1", (str(name).strip(),))
    if not rows:
        return None
    course_id = int(rows[0]["id"])
    if course_id not in _running:
        _workers.submit(_run_course, course_id)
    return course_id

def install(app: Any) -> None:
    _setup()
    if not any(getattr(route, "path", "") == "/settings" for route in app.routes):
        app.router.routes[0:0] = router.routes
    app._myai_settings_installed = True

    api_module: Any = __import__("my_ai.api", fromlist=["page"])
    original_page = getattr(api_module, "page", None)
    if original_page is not None and not getattr(app, "_myai_page_patched", False):
        app._myai_page_patched = True
        def page_with_learning():
            html = original_page()
            link = "<a href='/settings' style='float:left;padding:6px 10px;background:#e0e7ff;border-radius:7px;text-decoration:none'>تنظیمات</a>"
            return html.replace("<h1>My-AI ", "<h1>My-AI "+link+" ", 1)
        api_module.page = page_with_learning

