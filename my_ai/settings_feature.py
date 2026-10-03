from __future__ import annotations

import json
import logging
import httpx
import re
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from .auth import require_admin, require_user, audit
from .db import connect, execute, fetch_all, init_db
from .git_connector import GitHubConnector
from .llm import create_llm
from .provider_catalog import list_providers, upsert_provider, delete_provider, list_models, upsert_model, delete_model, export_catalog, add_provider_key, list_provider_keys, rotate_provider_key, activate_provider_key, set_routing_rule, list_routing_rules, delete_routing_rule, set_fallback_chain, list_fallback_chain, delete_fallback_chain
from .settings_store import get_setting, set_setting, get_bool, get_int, get_github_settings, get_setting_registry, get_configuration_schema_version, reset_setting, export_registered_settings, import_registered_settings, list_setting_history
from .ui_actions import UIAction, list_ui_actions, register_ui_action
from .metrics import snapshot as metrics_snapshot
from .no_code_catalog import inventory as no_code_inventory
from .config_profiles import save_profile, active_profile, load_profile
from .learning_catalog import add_source, list_sources, review_source, update_content_hash, update_source, delete_source, list_relearning_queue
from .backup_manager import backup as backup_database, restore as restore_database, prune_backups
from .control_plane import list_records, get_record, put_record, set_enabled, delete_record, start_action, update_action, get_action, list_actions, namespace_catalog
from .registries import publish_prompt, activate_prompt, publish_policy, register_tool, update_tool, list_tools, list_prompt_history, rollback_prompt, prompt_diff
from .plugin_registry import propose_plugin, approve_plugin, reject_plugin
from .evaluation_registry import upsert_suite, list_suites, create_baseline, propose_candidate, get_candidate, verify_candidate, list_candidates, compare_metrics
from .integration_catalog import register_integration, list_integrations, register_webhook, list_webhooks, map_event_action, list_event_actions
from .security_catalog import define_role, define_capability, set_permission, set_network_policy, set_filesystem_policy, set_subprocess_policy, set_self_modification_policy, list_security_policies
from .registries import publish_workflow, update_workflow, list_workflows

router = APIRouter(tags=["settings"])  # roadmap curriculum extraction integration
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
 evidence_json TEXT NOT NULL DEFAULT '[]',
 provenance_json TEXT NOT NULL DEFAULT '{}',
 UNIQUE(course_id,topic_id),
 FOREIGN KEY(course_id) REFERENCES custom_courses(id) ON DELETE CASCADE,
 FOREIGN KEY(topic_id) REFERENCES custom_course_topics(id) ON DELETE CASCADE
);
"""


class ProviderCatalogRequest(BaseModel):
    provider_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1, max_length=120)
    protocol: str = Field(min_length=1, max_length=80)
    endpoint: str = Field(min_length=1, max_length=1000)
    auth_type: str = Field(default="none", max_length=40)
    secret: str = Field(default="", max_length=10000)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    version: str = Field(default="", max_length=120)
    timeout_seconds: float = Field(default=30, gt=0, le=3600)
    enabled: bool = True

class ModelCatalogRequest(BaseModel):
    provider_id: int = Field(gt=0)
    model_id: str = Field(min_length=1, max_length=300)
    tasks: list[str] = Field(default_factory=list, max_length=30)
    context_length: int | None = Field(default=None, gt=0)
    limits: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=100, ge=0, le=100000)
    version: str = Field(default="", max_length=120)
    enabled: bool = True

class RoutingRuleRequest(BaseModel):
    task: str = Field(min_length=1, max_length=80)
    model_id: str = Field(min_length=1, max_length=300)
    provider_id: int | None = Field(default=None, gt=0)
    priority: int = Field(default=100, ge=0, le=100000)
    enabled: bool = True

class FallbackChainRequest(BaseModel):
    name: str = Field(default="ui", min_length=1, max_length=100)
    task: str = Field(default="general", min_length=1, max_length=80)
    model_ids: list[str] = Field(min_length=1, max_length=50)
    enabled: bool = True

class CourseRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    topics: list[dict[str, str]] = Field(min_length=1, max_length=100)
    llm_model: str = Field(default="", max_length=300)
    schedule: str = Field(default="weekly", max_length=120)
    mastery_threshold: float = Field(default=0.8, ge=0, le=1)
    source_policy: str = Field(default="hybrid", max_length=40)
    mode: str = Field(default="auto", max_length=40)

class CurriculumExtractRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    sources: list[str] = Field(min_length=1, max_length=10)
    llm_model: str = Field(default="", max_length=300)
    schedule: str = Field(default="weekly", max_length=120)
    mastery_threshold: float = Field(default=0.8, ge=0, le=1)
    source_policy: str = Field(default="hybrid", max_length=40)
    mode: str = Field(default="auto", max_length=40)

class CourseTopicRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    goal: str = Field(default="", max_length=2000)
    source_url: str = Field(default="", max_length=1000)

class CourseUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    llm_model: str = Field(default="", max_length=300)
    schedule: str = Field(default="weekly", max_length=120)
    mastery_threshold: float = Field(default=0.8, ge=0, le=1)
    source_policy: str = Field(default="hybrid", max_length=40)
    mode: str = Field(default="auto", max_length=40)


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
        course_columns={str(r["name"]) for r in conn.execute("PRAGMA table_info(custom_courses)").fetchall()}
        for column, ddl in {
            "llm_model":"TEXT NOT NULL DEFAULT ''",
            "schedule":"TEXT NOT NULL DEFAULT 'weekly'",
            "mastery_threshold":"REAL NOT NULL DEFAULT 0.8",
            "source_policy":"TEXT NOT NULL DEFAULT 'hybrid'",
            "mode":"TEXT NOT NULL DEFAULT 'auto'",
        }.items():
            if column not in course_columns:
                conn.execute(f"ALTER TABLE custom_courses ADD COLUMN {column} {ddl}")
        progress_columns = {str(r["name"]) for r in conn.execute("PRAGMA table_info(custom_course_progress)").fetchall()}
        for column, ddl in {
            "evidence_json": "TEXT NOT NULL DEFAULT '[]'",
            "provenance_json": "TEXT NOT NULL DEFAULT '{}'",
        }.items():
            if column not in progress_columns:
                conn.execute(f"ALTER TABLE custom_course_progress ADD COLUMN {column} {ddl}")
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
        COALESCE(p.phase,'planned') phase,p.lesson,p.score,p.updated_at,p.last_attempt_at,COALESCE(p.evidence_json,'[]') evidence_json,COALESCE(p.provenance_json,'{}') provenance_json
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
    except Exception as exc:
        logging.getLogger(__name__).debug("learning_domains migration already applied: %s", exc)
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
    except Exception as exc:
        logging.getLogger(__name__).debug("learning source discovery failed: %s", exc)
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


def _set_topic(topic_id: int, status: str, progress: float, phase: str, lesson: str | None = None, score: float | None = None, evidence: list[dict[str, Any]] | None = None, provenance: dict[str, Any] | None = None) -> None:
    execute("UPDATE custom_course_progress SET status=?,progress_percent=?,phase=?,lesson=COALESCE(?,lesson),score=COALESCE(?,score),evidence_json=COALESCE(?,evidence_json),provenance_json=COALESCE(?,provenance_json),updated_at=CURRENT_TIMESTAMP WHERE topic_id=?", (status, max(0,min(100,float(progress))), phase, lesson, score, json.dumps(evidence, ensure_ascii=False) if evidence is not None else None, json.dumps(provenance, ensure_ascii=False) if provenance is not None else None, topic_id))


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
    evidence = [{"type": "source", "url": topic.get("source_url"), "scope": topic.get("goal", "")}] if topic.get("source_url") else []
    provenance = {"course_id": course_id, "topic_id": topic_id, "source_url": topic.get("source_url"), "recorded_at": datetime.now(timezone.utc).isoformat()}
    _set_topic(topic_id, "started", 70, "assessment", lesson=lesson, evidence=evidence, provenance=provenance)
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


class SettingsImportRequest(BaseModel):
    values: dict[str, Any]

@router.get("/settings/audit")
def settings_audit(request: Request, limit: int = 200):
    require_admin(request)
    rows=fetch_all("SELECT id,user_id,username,tool_name,action,status,details,created_at FROM audit_log ORDER BY id DESC LIMIT ?",(max(1,min(1000,int(limit))),))
    return {"items":[dict(r) for r in rows]}

@router.get("/settings/workflows")
def settings_workflows(request: Request):
    require_admin(request); return {"items": list_workflows()}

@router.post("/settings/workflows")
def settings_workflow(payload: ControlPlaneRecordRequest, request: Request):
    user=require_admin(request); stages=payload.payload.get("stages", [])
    if not isinstance(stages,list): raise HTTPException(400,"stages must be a list")
    item=publish_workflow(payload.name,stages,version=str(payload.payload.get("version","1")),enabled=payload.enabled); audit(user,"workflows","write","200",payload.name); return item

@router.put("/settings/workflows/{name}")
def settings_workflow_update(name: str, payload: ControlPlaneRecordRequest, request: Request):
    user=require_admin(request); stages=payload.payload.get("stages", [])
    if payload.name != name or not isinstance(stages,list): raise HTTPException(400,"invalid workflow update")
    try: item=update_workflow(name,stages,version=str(payload.payload.get("version","1")),enabled=payload.enabled)
    except KeyError as exc: raise HTTPException(404,"workflow not found") from exc
    audit(user,"workflows","update","200",name); return item

@router.get("/settings/security-policies")
def settings_security_policies(request: Request):
    require_admin(request); return list_security_policies()

@router.post("/settings/security/roles")
def settings_security_role(payload: ControlPlaneRecordRequest, request: Request):
    user=require_admin(request); caps=payload.payload.get("capabilities", [])
    if not isinstance(caps,list): raise HTTPException(400,"capabilities must be a list")
    item=define_role(payload.name,[str(x) for x in caps],version=str(payload.payload.get("version","1")),enabled=payload.enabled); audit(user,"security","role-write","200",payload.name); return item

@router.post("/settings/security/capabilities")
def settings_security_capability(payload: ControlPlaneRecordRequest, request: Request):
    user=require_admin(request); actions=payload.payload.get("actions", [])
    if not isinstance(actions,list): raise HTTPException(400,"actions must be a list")
    item=define_capability(payload.name,[str(x) for x in actions],resource=str(payload.payload.get("resource","*")),version=str(payload.payload.get("version","1"))); audit(user,"security","capability-write","200",payload.name); return item

@router.post("/settings/security/permissions")
def settings_security_permission(payload: ControlPlaneRecordRequest, request: Request):
    user=require_admin(request); p=payload.payload
    item=set_permission(str(p.get("role") or payload.name),str(p.get("resource") or "*"),[str(x) for x in (p.get("actions") or [])],users=p.get("users") or []); audit(user,"security","permission-write","200",payload.name); return item

@router.post("/settings/security/network")
def settings_security_network(payload: ControlPlaneRecordRequest, request: Request):
    user=require_admin(request); p=payload.payload
    item=set_network_policy(payload.name,p.get("allowlist") or [],p.get("denylist") or [],default=str(p.get("default","deny"))); audit(user,"security","network-write","200",payload.name); return item

@router.post("/settings/security/filesystem")
def settings_security_filesystem(payload: ControlPlaneRecordRequest, request: Request):
    user=require_admin(request); p=payload.payload
    item=set_filesystem_policy(payload.name,p.get("roots") or [],read=bool(p.get("read",True)),write=bool(p.get("write",False))); audit(user,"security","filesystem-write","200",payload.name); return item

@router.post("/settings/security/self-modification")
def settings_security_self_modification(payload: ControlPlaneRecordRequest, request: Request):
    user=require_admin(request); p=payload.payload
    item=set_self_modification_policy(payload.name,p.get("allowed_paths") or [],bool(p.get("require_approval",True)),bool(p.get("require_tests",True))); audit(user,"security","self-modification-write","200",payload.name); return item

@router.post("/settings/security/subprocess")
def settings_security_subprocess(payload: ControlPlaneRecordRequest, request: Request):
    user=require_admin(request); p=payload.payload
    item=set_subprocess_policy(payload.name,p.get("commands") or [],timeout=float(p.get("timeout",30))); audit(user,"security","subprocess-write","200",payload.name); return item

@router.get("/settings/capabilities")
def settings_capability_inventory(request: Request):
    require_admin(request)
    return no_code_inventory()

@router.get("/settings/metrics")
def settings_metrics(request: Request):
    require_admin(request)
    return metrics_snapshot()

class UIActionRequest(BaseModel):
    id: str = Field(min_length=1, max_length=160)
    module: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    method: str = Field(default="GET", pattern="^(GET|POST)$")
    endpoint: str = Field(min_length=1, max_length=1000)
    permission: str = Field(min_length=1, max_length=160)
    confirmation: bool = False

@router.get("/settings/ui-actions")
def settings_ui_actions(request: Request):
    require_admin(request)
    return {"items": list_ui_actions()}

@router.post("/settings/ui-actions")
def settings_ui_action_register(payload: UIActionRequest, request: Request):
    user=require_admin(request)
    item=register_ui_action(UIAction(**payload.model_dump()))
    audit(user,"ui","action-register","200",payload.id)
    return item

class ProviderKeyRequest(BaseModel):
    key_name: str = Field(min_length=1, max_length=120)
    secret: str = Field(min_length=1, max_length=10000)
    priority: int = Field(default=100, ge=0, le=100000)

@router.get("/settings/providers/{provider_id}/keys")
def settings_provider_keys(provider_id:int, request:Request):
    require_admin(request); return {"items":list_provider_keys(provider_id)}

@router.post("/settings/providers/{provider_id}/keys")
def settings_provider_key_add(provider_id:int,payload:ProviderKeyRequest,request:Request):
    require_admin(request)
    try: return add_provider_key(provider_id,payload.key_name,payload.secret,priority=payload.priority)
    except ValueError as exc: raise HTTPException(422,str(exc))

@router.post("/settings/providers/{provider_id}/keys/rotate")
def settings_provider_key_rotate(provider_id:int,request:Request):
    user=require_admin(request)
    try:
        result=rotate_provider_key(provider_id)
    except ValueError as exc:
        raise HTTPException(422,str(exc))
    audit(user,"models","key-rotate","200",str(provider_id))
    return result

@router.post("/settings/providers/{provider_id}/keys/{key_name}/activate")
def settings_provider_key_activate(provider_id:int,key_name:str,request:Request):
    user=require_admin(request)
    try:
        result=activate_provider_key(provider_id,key_name)
    except ValueError as exc:
        raise HTTPException(422,str(exc))
    audit(user,"models","key-activate","200",f"{provider_id}:{key_name}")
    return result

@router.get("/settings/routing")
def settings_routing(request: Request):
    require_admin(request)
    return {"rules": list_routing_rules(), "fallbacks": {task: list_fallback_chain("ui", task) for task in ("general","chat","coding","reasoning","embedding")}}

@router.put("/settings/routing/rule")
def settings_routing_rule(payload: RoutingRuleRequest, request: Request):
    user=require_admin(request)
    item=set_routing_rule(payload.task,payload.model_id,provider_id=payload.provider_id,priority=payload.priority,enabled=payload.enabled)
    audit(user,"models","routing-write","200",payload.task)
    return item

@router.delete("/settings/routing/rule/{task}")
def settings_routing_rule_delete(task: str, request: Request):
    user=require_admin(request)
    ok=delete_routing_rule(task)
    audit(user,"models","routing-delete","200",task)
    return {"deleted":ok,"task":task}

@router.put("/settings/routing/fallback")
def settings_routing_fallback(payload: FallbackChainRequest, request: Request):
    user=require_admin(request)
    item=set_fallback_chain(payload.name,payload.task,payload.model_ids,enabled=payload.enabled)
    audit(user,"models","fallback-write","200",payload.task)
    return {"items":item}

@router.delete("/settings/routing/fallback/{task}")
def settings_routing_fallback_delete(task: str, request: Request):
    user=require_admin(request)
    ok=delete_fallback_chain("ui",task)
    audit(user,"models","fallback-delete","200",task)
    return {"deleted":ok,"task":task}

@router.get("/settings/providers")
def settings_providers(request: Request):
    require_admin(request)
    return {"providers": list_providers(), "models": list_models()}

@router.post("/settings/providers")
def settings_provider_create(payload: ProviderCatalogRequest, request: Request):
    require_admin(request)
    try:
        return upsert_provider(**payload.model_dump())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

@router.delete("/settings/providers/{provider_id}")
def settings_provider_delete(provider_id: int, request: Request):
    require_admin(request)
    delete_provider(provider_id)
    return {"deleted": provider_id}

@router.post("/settings/models")
def settings_model_create(payload: ModelCatalogRequest, request: Request):
    require_admin(request)
    try:
        return upsert_model(**payload.model_dump())
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

@router.get("/settings/models/export")
def settings_models_export(request: Request):
    require_admin(request)
    return export_catalog()

@router.delete("/settings/models/{provider_id}/{model_id:path}")
def settings_model_delete(provider_id: int, model_id: str, request: Request):
    require_admin(request)
    delete_model(provider_id, model_id)
    return {"deleted": {"provider_id": provider_id, "model_id": model_id}}

@router.post("/settings/providers/{provider_id}/health")
def settings_provider_health(provider_id: int, request: Request):
    require_admin(request)
    provider = next((x for x in list_providers() if int(x["id"]) == int(provider_id)), None)
    if not provider:
        raise HTTPException(404, "Provider not found.")
    from .provider_catalog import get_provider_runtime_config
    runtime = get_provider_runtime_config(provider_id)
    started = __import__("time").perf_counter()
    headers = {}
    secret = str(runtime.get("api_key") or "")
    if secret and str(runtime.get("auth_type") or "none").lower() != "none":
        header = str(runtime.get("auth_header") or "Authorization")
        scheme = str(runtime.get("auth_scheme") or "Bearer")
        headers[header] = f"{scheme} {secret}" if scheme else secret
    try:
        response = httpx.get(str(provider["endpoint"]).rstrip("/") + "/models", headers=headers,
                             timeout=float(provider.get("timeout_seconds") or 30))
        elapsed = round((__import__("time").perf_counter() - started) * 1000, 2)
        response.raise_for_status()
        return {"provider_id": provider_id, "healthy": True, "status_code": response.status_code, "latency_ms": elapsed}
    except Exception as exc:
        return {"provider_id": provider_id, "healthy": False,
                "latency_ms": round((__import__("time").perf_counter() - started) * 1000, 2),
                "error": str(exc)}

@router.post("/settings/models/{provider_id}/{model_id:path}/health")
def settings_model_health(provider_id: int, model_id: str, request: Request):
    require_admin(request)
    provider = next((x for x in list_providers() if int(x["id"]) == int(provider_id)), None)
    if not provider:
        raise HTTPException(404, "Provider not found.")
    started = __import__("time").perf_counter()
    try:
        response = httpx.get(str(provider["endpoint"]).rstrip("/") + "/models",
                             timeout=float(provider.get("timeout_seconds") or 30))
        response.raise_for_status()
        payload = response.json()
        models = {str(item.get("id")) for item in payload.get("data", []) if isinstance(item, dict) and item.get("id")}
        available = model_id in models if models else True
        return {"provider_id": provider_id, "model": model_id, "available": available,
                "latency_ms": round((__import__("time").perf_counter() - started) * 1000, 2)}
    except Exception as exc:
        return {"provider_id": provider_id, "model": model_id, "available": False,
                "latency_ms": round((__import__("time").perf_counter() - started) * 1000, 2),
                "error": str(exc)}

class LearningSourceRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2000)
    course_id: int | None = None
    topic_id: int | None = None
    source_type: str = "custom"
    title: str = ""
    priority: int = Field(default=100, ge=0)
    weight: float = Field(default=1, ge=0)
    product: str = ""
    version: str = ""
    compatibility: str = ""
    provenance: dict[str, Any] = Field(default_factory=dict)

@router.get("/settings/learning-sources")
def learning_sources_list(request: Request, course_id: int | None = None, topic_id: int | None = None, status: str | None = None):
    require_admin(request)
    return {"items": list_sources(course_id, topic_id, status)}

@router.post("/settings/learning-sources")
def learning_source_add(payload: LearningSourceRequest, request: Request):
    user=require_admin(request)
    item=add_source(**payload.model_dump())
    audit(user,"learning","source-add","200",str(item["id"]))
    return item

@router.put("/settings/learning-sources/{source_id}")
def settings_learning_source_update(source_id: int, payload: LearningSourceRequest, request: Request):
    user=require_admin(request)
    item=update_source(source_id,**payload.model_dump(exclude_unset=True))
    if item is None: raise HTTPException(404,"Learning source not found.")
    audit(user,"learning","source-update","200",str(source_id))
    return item

@router.delete("/settings/learning-sources/{source_id}")
def settings_learning_source_delete(source_id: int, request: Request):
    user=require_admin(request)
    ok=delete_source(source_id)
    audit(user,"learning","source-delete","200",str(source_id))
    return {"deleted":ok,"source_id":source_id}

@router.get("/settings/learning-sources/relearning")
def settings_learning_relearning(request: Request, status: str = "pending", limit: int = 100):
    require_admin(request)
    return {"items": list_relearning_queue(status=status,limit=limit)}

@router.post("/settings/learning-sources/upload")
async def learning_source_upload(request: Request, file: UploadFile = File(...), course_id: int | None = None, topic_id: int | None = None,
                                 source_type: str = "file", priority: int = 100, weight: float = 1):
    user=require_admin(request)
    if source_type not in {"file","book","repository","custom"}:
        raise HTTPException(422,"Unsupported source type for uploaded file.")
    filename=Path(file.filename or "source.bin").name
    if not filename or filename in {".",".."}:
        raise HTTPException(422,"Invalid filename.")
    root=Path(str(get_setting("execution.project_root","projects"))).expanduser().resolve()
    target_dir=(root / ".myai" / "learning_sources").resolve()
    target_dir.mkdir(parents=True,exist_ok=True)
    target=(target_dir / filename).resolve()
    if target.parent != target_dir:
        raise HTTPException(422,"Invalid upload path.")
    content=await file.read()
    max_bytes=int(get_setting("learning.source_max_bytes",25*1024*1024))
    if len(content)>max_bytes:
        raise HTTPException(413,"Uploaded source exceeds configured size limit.")
    target.write_bytes(content)
    item=add_source(url=target.as_uri(),course_id=course_id,topic_id=topic_id,source_type=source_type,title=filename,
                    priority=priority,weight=weight,provenance={"uploaded":True,"filename":filename,"size":len(content)})
    audit(user,"learning","source-upload","200",str(item["id"]))
    return item

@router.post("/settings/learning-sources/{source_id}/{status}")
def learning_source_review(source_id:int,status:str,request:Request):
    user=require_admin(request)
    try: item=review_source(source_id,status)
    except ValueError as exc: raise HTTPException(422,str(exc))
    audit(user,"learning","source-review","200",f"{source_id}:{status}")
    return item

@router.post("/settings/learning-sources/{source_id}/hash")
def learning_source_hash(source_id:int, request:Request, content:str=""):
    require_admin(request)
    return update_content_hash(source_id,content)

class BackupRequest(BaseModel):
    path: str = Field(default="", max_length=2000)
    confirm: bool = False
    overwrite: bool = False
    password: str | None = Field(default=None, min_length=12, max_length=10000)

@router.post("/settings/database/backup")
def settings_database_backup(payload: BackupRequest, request: Request):
    user=require_admin(request)
    destination = payload.path
    if not destination.strip():
        destination = str(get_setting("database.backup.destination", "data/backups"))
    destination_path = Path(destination)
    if destination_path.suffix == "":
        destination_path.mkdir(parents=True, exist_ok=True)
        destination = str(destination_path / f"my_ai-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.db")
    try:
        result=backup_database(destination,overwrite=payload.overwrite,password=payload.password)
        retention=get_int("database.backup.retention", 7)
        result["removed"]=prune_backups(str(Path(destination).parent), retention)
    except (OSError,FileNotFoundError,FileExistsError) as exc: raise HTTPException(400,str(exc))
    audit(user,"database","backup","200",result["path"]); return result

@router.get("/settings/database/health")
def settings_database_health(request: Request):
    require_admin(request)
    with connect() as conn:
        integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_keys = int(conn.execute("PRAGMA foreign_key_check").fetchone()[0]) if conn.execute("PRAGMA foreign_key_check").fetchone() else 0
        tables = int(conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0])
    return {"ok": integrity == "ok" and foreign_keys == 0, "integrity": integrity, "foreign_key_errors": foreign_keys, "table_count": tables}


@router.post("/settings/database/restore")
def settings_database_restore(payload: BackupRequest, request: Request):
    user=require_admin(request)
    if not payload.confirm:
        raise HTTPException(400, "Restore requires explicit confirmation.")
    try: result=restore_database(payload.path,password=payload.password)
    except (OSError,FileNotFoundError) as exc: raise HTTPException(400,str(exc))
    audit(user,"database","restore","200",result["path"]); return result

@router.get("/settings/control-plane/namespaces")
def control_plane_namespaces(request: Request):
    require_admin(request)
    return {"items": namespace_catalog()}

@router.get("/settings/control-plane")
def control_plane_list(request: Request, namespace: str | None = None, include_disabled: bool = True):
    require_admin(request)
    return {"items": list_records(namespace, include_disabled)}

@router.get("/settings/control-plane/{namespace}/{name}")
def control_plane_get(namespace: str, name: str, request: Request):
    require_admin(request)
    item = get_record(namespace, name)
    if not item:
        raise HTTPException(404, "Control-plane record not found.")
    return item

@router.put("/settings/control-plane/{namespace}")
def control_plane_put(namespace: str, payload: ControlPlaneRecordRequest, request: Request):
    user = require_admin(request)
    item = put_record(namespace, payload.name, payload.payload, enabled=payload.enabled)
    audit(user, "control-plane", "put", "200", f"{namespace}/{payload.name}")
    return item

@router.post("/settings/control-plane/{namespace}/{name}/enable")
def control_plane_enable(namespace: str, name: str, request: Request):
    user = require_admin(request)
    try:
        item = set_enabled(namespace, name, True)
    except KeyError:
        raise HTTPException(404, "Control-plane record not found.")
    audit(user, "control-plane", "enable", "200", f"{namespace}/{name}")
    return item

@router.post("/settings/control-plane/{namespace}/{name}/disable")
def control_plane_disable(namespace: str, name: str, request: Request):
    user = require_admin(request)
    try:
        item = set_enabled(namespace, name, False)
    except KeyError:
        raise HTTPException(404, "Control-plane record not found.")
    audit(user, "control-plane", "disable", "200", f"{namespace}/{name}")
    return item

@router.delete("/settings/control-plane/{namespace}/{name}")
def control_plane_delete(namespace: str, name: str, request: Request):
    user = require_admin(request)
    deleted = delete_record(namespace, name)
    audit(user, "control-plane", "delete", "200", f"{namespace}/{name}")
    return {"deleted": deleted, "namespace": namespace, "name": name}

@router.post("/settings/control-plane/actions")
def control_plane_start_action(payload: ControlPlaneActionRequest, request: Request):
    user = require_admin(request)
    item = start_action(payload.action, payload.namespace, payload.target_id)
    audit(user, "control-plane", "action-start", "200", item["id"])
    return item

@router.put("/settings/control-plane/actions/{action_id}")
def control_plane_update_action(action_id: str, payload: ControlPlaneActionUpdateRequest, request: Request):
    user = require_admin(request)
    try:
        item = update_action(action_id, status=payload.status, progress=payload.progress, result=payload.result, error=payload.error)
    except KeyError:
        raise HTTPException(404, "Action not found.")
    audit(user, "control-plane", "action-update", "200", action_id)
    return item

@router.get("/settings/control-plane/actions/{action_id}")
def control_plane_get_action(action_id: str, request: Request):
    require_admin(request)
    try:
        return get_action(action_id)
    except KeyError:
        raise HTTPException(404, "Action not found.")

@router.get("/settings/control-plane/actions")
def control_plane_list_actions(request: Request, limit: int = 100):
    require_admin(request)
    return {"items": list_actions(limit)}

@router.get("/settings/registry/history")
def settings_registry_history(request: Request, key: str | None = None, limit: int = 200):
    require_admin(request)
    return {"items": list_setting_history(key, limit)}

@router.get("/settings/registry")
def settings_registry(request: Request):
    require_admin(request)
    items = []
    for key, meta in get_setting_registry().items():
        item = dict(meta)
        item["key"] = key
        item["value"] = "" if meta.get("secret") else get_setting(key, meta["default"])
        items.append(item)
    return {"version": get_configuration_schema_version(), "items": items}

@router.get("/settings/registry/export")
def export_settings_registry(request: Request):
    require_admin(request)
    return {"version": get_configuration_schema_version(), "settings": export_registered_settings()}

@router.post("/settings/registry/import")
def import_settings_registry(payload: SettingsImportRequest, request: Request):
    user = require_admin(request)
    try:
        values = import_registered_settings(payload.values)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    audit(user, "settings", "import", "200", f"settings-import:{len(payload.values)}")
    return {"version": get_configuration_schema_version(), "settings": values, "imported": len(payload.values)}

class EvaluationSuiteRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    tasks: list[dict[str, Any]] = Field(min_length=1, max_length=1000)
    version: str = Field(default="1", max_length=120)
    enabled: bool = True

class EvaluationBaselineRequest(BaseModel):
    suite_id: int = Field(gt=0)
    label: str = Field(min_length=1, max_length=200)
    metrics: dict[str, Any] = Field(default_factory=dict)

class EvaluationCandidateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    payload: dict[str, Any] = Field(default_factory=dict)
    baseline_run_id: int | None = Field(default=None, gt=0)

class EvaluationVerificationRequest(BaseModel):
    verification: dict[str, Any] = Field(default_factory=dict)
    approved: bool = False

@router.get("/settings/evaluation/suites")
def settings_evaluation_suites(request: Request):
    require_admin(request)
    return {"items": list_suites()}

@router.post("/settings/evaluation/suites")
def settings_evaluation_suite(payload: EvaluationSuiteRequest, request: Request):
    user=require_admin(request)
    item=upsert_suite(payload.name,payload.tasks,payload.version,payload.enabled)
    audit(user,"evaluation","suite-write","200",payload.name)
    return item

@router.post("/settings/evaluation/baselines")
def settings_evaluation_baseline(payload: EvaluationBaselineRequest, request: Request):
    user=require_admin(request)
    item=create_baseline(payload.suite_id,payload.label,payload.metrics)
    audit(user,"evaluation","baseline-write","200",payload.label)
    return item

@router.get("/settings/evaluation/candidates")
def settings_evaluation_candidates(request: Request):
    require_admin(request)
    return {"items": list_candidates()}

@router.post("/settings/evaluation/candidates")
def settings_evaluation_candidate(payload: EvaluationCandidateRequest, request: Request):
    user=require_admin(request)
    item=propose_candidate(payload.name,payload.payload,payload.baseline_run_id)
    audit(user,"evaluation","candidate-propose","200",item["candidate_id"])
    return item

@router.post("/settings/evaluation/candidates/{candidate_id}/verify")
def settings_evaluation_candidate_verify(candidate_id: str, payload: EvaluationVerificationRequest, request: Request):
    user=require_admin(request)
    if not get_candidate(candidate_id):
        raise HTTPException(404,"Evaluation candidate not found.")
    item=verify_candidate(candidate_id,payload.verification,payload.approved)
    audit(user,"evaluation","candidate-verify","200",candidate_id)
    return item

class ControlPlaneRecordRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    payload: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True

class ControlPlaneActionRequest(BaseModel):
    action: str = Field(min_length=1, max_length=100)
    namespace: str = Field(min_length=1, max_length=120)
    target_id: str | None = Field(default=None, max_length=200)

class ControlPlaneActionUpdateRequest(BaseModel):
    status: str = Field(min_length=1, max_length=40)
    progress: float = Field(default=0, ge=0, le=100)
    result: dict[str, Any] = Field(default_factory=dict)
    error: str = ""

class SettingsRegistryValueRequest(BaseModel):
    value: Any

@router.put("/settings/registry/{key:path}")
def update_registered_setting(key: str, payload: SettingsRegistryValueRequest, request: Request):
    user = require_admin(request)
    registry = get_setting_registry()
    if key not in registry:
        raise HTTPException(404, "Unknown registered setting.")
    try:
        set_setting(key, payload.value, secret=bool(registry[key].get("secret")))
        value = "" if registry[key].get("secret") else get_setting(key, registry[key]["default"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    audit(user, "settings", "update", "200", f"setting-update:{key}")
    return {"key": key, "value": value}

@router.delete("/settings/registry/{key:path}")
def delete_registered_setting(key: str, request: Request):
    user = require_admin(request)
    if key not in get_setting_registry():
        raise HTTPException(404, "Unknown registered setting.")
    value = reset_setting(key)
    audit(user, "settings", "delete", "200", f"setting-delete:{key}")
    return {"key": key, "value": value, "deleted": True}

@router.post("/settings/registry/{key:path}/reset")
def reset_registered_setting(key: str, request: Request):
    user = require_admin(request)
    if key not in get_setting_registry():
        raise HTTPException(404, "Unknown registered setting.")
    value = reset_setting(key)
    audit(user, "settings", "reset", "200", f"setting-reset:{key}")
    return {"key": key, "value": value, "reset": True}

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
        "observability": {
            "alerts_enabled": get_bool("observability.alerts_enabled", True),
            "alert_rules": json.loads(str(get_setting("observability.alert_rules", "[]")) or "[]"),
            "notification_destinations": json.loads(str(get_setting("observability.notification_destinations", "[]")) or "[]"),
            "dashboard_config": json.loads(str(get_setting("observability.dashboard_config", "{}")) or "{}"),
            "diagnostics_export": str(get_setting("observability.diagnostics_export", "json")),
        },
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

class ProfileRequest(BaseModel):
    name: str
    settings: dict[str, Any] = Field(default_factory=dict)
    activate: bool = False

@router.get("/settings/profiles")
def settings_profiles(request: Request):
    require_admin(request)
    from .control_plane import list_records
    return {"items": list_records("config.profiles"), "active": active_profile()}

@router.post("/settings/profiles")
def settings_profile_save(payload: ProfileRequest, request: Request):
    user = require_admin(request)
    item = save_profile(payload.name, payload.settings, activate=payload.activate)
    audit(user, "profiles", "write", "200", payload.name)
    return item

@router.get("/settings/profiles/{name}")
def settings_profile_load(name: str, request: Request):
    require_admin(request)
    try:
        return {"name": name, "settings": load_profile(name), "active": active_profile() == name}
    except KeyError:
        raise HTTPException(404, "Profile not found.")

class PromptRegistryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=100000)
    task: str = Field(default="default", max_length=120)
    version: str = Field(default="1", max_length=120)
    enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

class PolicyRegistryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    policy: dict[str, Any] = Field(default_factory=dict)
    version: str = Field(default="1", max_length=120)
    enabled: bool = False

class ToolRegistryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list, max_length=50)
    timeout: float = Field(default=30, gt=0, le=3600)
    retries: int = Field(default=2, ge=0, le=20)
    tasks: list[str] = Field(default_factory=list, max_length=50)
    version: str = Field(default="1", max_length=120)
    enabled: bool = False

class PluginProposalRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=2000)
    version: str = Field(default="", max_length=120)
    capabilities: list[str] = Field(default_factory=list)
    checksum: str = Field(default="", max_length=500)

@router.get("/settings/prompts")
def settings_prompts(request: Request):
    require_admin(request); return {"items": list_records("prompts.registry")}

@router.post("/settings/prompts")
def settings_prompt_publish(payload: PromptRegistryRequest, request: Request):
    user=require_admin(request); item=publish_prompt(payload.name,payload.text,task=payload.task,version=payload.version,enabled=payload.enabled,metadata=payload.metadata); audit(user,"prompts","write","200",payload.name); return item

@router.get("/settings/prompts/{name}/history")
def settings_prompt_history(name: str, request: Request):
    require_admin(request); return {"items": list_prompt_history(name)}

@router.post("/settings/prompts/{name}/rollback/{version}")
def settings_prompt_rollback(name: str, version: int, request: Request):
    user=require_admin(request)
    try: item=rollback_prompt(name, version)
    except KeyError as exc: raise HTTPException(404, "prompt version not found") from exc
    audit(user, "prompts", "rollback", "200", f"{name}@{version}"); return item

@router.get("/settings/prompts/{name}/diff")
def settings_prompt_diff(name: str, from_version: int, to_version: int, request: Request):
    require_admin(request)
    try: return prompt_diff(name, from_version, to_version)
    except KeyError as exc: raise HTTPException(404, "prompt version not found") from exc

@router.post("/settings/prompts/{name}/activate")
def settings_prompt_activate(name: str, request: Request):
    user=require_admin(request); item=activate_prompt(name); audit(user,"prompts","activate","200",name); return item

@router.get("/settings/policies")
def settings_policies(request: Request):
    require_admin(request); return {"items": list_records("policies.registry")}

@router.post("/settings/policies")
def settings_policy_publish(payload: PolicyRegistryRequest, request: Request):
    user=require_admin(request); item=publish_policy(payload.name,payload.policy,version=payload.version,enabled=payload.enabled); audit(user,"policies","write","200",payload.name); return item

@router.get("/settings/tools")
def settings_tools(request: Request):
    require_admin(request); return {"items": list_tools()}

@router.post("/settings/tools")
def settings_tool_register(payload: ToolRegistryRequest, request: Request):
    user=require_admin(request)
    item=register_tool(
        payload.name,
        payload.description,
        payload.input_schema,
        payload.output_schema,
        permissions=payload.permissions,
        timeout=payload.timeout,
        retries=payload.retries,
        tasks=payload.tasks,
        version=payload.version,
        enabled=payload.enabled,
    )
    audit(user,"tools","write","200",payload.name)
    return item

@router.put("/settings/tools/{name}")
def settings_tool_update(name: str, payload: ToolRegistryRequest, request: Request):
    user=require_admin(request)
    if payload.name != name:
        raise HTTPException(400, "tool name mismatch")
    item=update_tool(name, payload.description, payload.input_schema, payload.output_schema,
                       permissions=payload.permissions, timeout=payload.timeout, retries=payload.retries,
                       tasks=payload.tasks, version=payload.version, enabled=payload.enabled)
    audit(user, "tools", "update", "200", name)
    return item

@router.get("/settings/integration-events")
def settings_integration_events(request: Request):
    require_admin(request); return {"items": list_event_actions()}

@router.post("/settings/integration-events")
def settings_integration_event(payload: ControlPlaneRecordRequest, request: Request):
    user=require_admin(request); action=str(payload.payload.get("action") or "").strip()
    if not action: raise HTTPException(400,"action is required")
    item=map_event_action(payload.name,action,enabled=payload.enabled); audit(user,"integrations","event-map","200",payload.name); return item

@router.get("/settings/integrations")
def settings_integrations(request: Request):
    require_admin(request); return {"items": list_integrations()}

@router.post("/settings/integrations")
def settings_integration(payload: ControlPlaneRecordRequest, request: Request):
    user=require_admin(request); item=register_integration(payload.name,payload.payload,payload.enabled); audit(user,"integrations","write","200",payload.name); return item

@router.get("/settings/webhooks")
def settings_webhooks(request: Request):
    require_admin(request); return {"items": list_webhooks()}

@router.post("/settings/webhooks")
def settings_webhook(payload: ControlPlaneRecordRequest, request: Request):
    user=require_admin(request); item=register_webhook(payload.name,payload.payload,payload.enabled); audit(user,"webhooks","write","200",payload.name); return item

@router.get("/settings/plugins")
def settings_plugins(request: Request):
    require_admin(request); return {"items": list_records("plugins.registry")}

@router.post("/settings/plugins")
def settings_plugin_propose(payload: PluginProposalRequest, request: Request):
    user=require_admin(request); item=propose_plugin(payload.name,payload.source,payload.version,payload.capabilities,payload.checksum); audit(user,"plugins","propose","200",payload.name); return item

@router.post("/settings/plugins/{name}/approve")
def settings_plugin_approve(name: str, request: Request):
    user=require_admin(request); item=approve_plugin(name); audit(user,"plugins","approve","200",name); return item

@router.post("/settings/plugins/{name}/reject")
def settings_plugin_reject(name: str, request: Request, reason: str = ""):
    user=require_admin(request); item=reject_plugin(name,reason); audit(user,"plugins","reject","200",name); return item

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

@router.get("/settings/courses/{course_id}/lessons/{topic_id}/evidence")
def course_lesson_evidence(course_id: int, topic_id: int, request: Request):
    require_admin(request); _setup()
    rows = fetch_all("""SELECT t.id,t.title,t.source_url,p.lesson,p.evidence_json,p.provenance_json
        FROM custom_course_topics t JOIN custom_course_progress p ON p.topic_id=t.id
        WHERE t.course_id=? AND t.id=?""", (course_id, topic_id))
    if not rows:
        raise HTTPException(404, "Lesson not found.")
    row = dict(rows[0])
    try: row["evidence"] = json.loads(row.pop("evidence_json") or "[]")
    except (TypeError, ValueError, json.JSONDecodeError): row["evidence"] = []
    try: row["provenance"] = json.loads(row.pop("provenance_json") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError): row["provenance"] = {}
    return row

@router.get("/settings/courses")
def courses(request: Request):
    require_admin(request)
    _setup()
    out=[]
    for c in fetch_all("SELECT * FROM custom_courses ORDER BY id"):
        s=_summary(int(c["id"])); c.update({"progress_percent":s["progress_percent"],"completed_topics":s["completed_topics"],"total_topics":s["total_topics"],"current":s["current"],"topics":s["topics"]}); out.append(c)
    return {"items":out}

@router.post("/settings/courses/extract-curriculum")
def extract_curriculum(r: CurriculumExtractRequest, request: Request):
    user = require_admin(request)
    _setup()
    from .web_learner import WebLearner
    urls = [str(url).strip() for url in r.sources if str(url).strip()]
    web = WebLearner()
    documents = []
    for url in urls:
        try:
            title, content = web.fetch(url)
        except Exception as exc:
            raise HTTPException(400, "Unable to read source URL.") from exc
        documents.append({"title": str(title), "url": url, "content": str(content)[:20000]})
    prompt = (
        "Extract a learning curriculum from these source documents. Return JSON only with "
        "an array named topics. Each topic needs title, goal, and source_url. Copy source_url "
        "only from supplied URLs. Do not invent URLs, do not duplicate titles, max 100 topics.\n"
        + json.dumps(documents, ensure_ascii=False)
    )
    try:
        raw = create_llm(r.llm_model.strip() or "general").chat(
            prompt, system="Extract curricula conservatively and return valid JSON only."
        )
        data = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "Curriculum extraction returned invalid JSON.") from exc
    topics = data.get("topics") if isinstance(data, dict) else None
    if not isinstance(topics, list):
        raise HTTPException(422, "Curriculum extraction returned no topics.")
    cleaned, seen = [], set()
    allowed_urls = set(urls)
    for item in topics[:100]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title or title.casefold() in seen:
            continue
        source_url = str(item.get("source_url") or "").strip()
        if source_url and source_url not in allowed_urls:
            source_url = ""
        seen.add(title.casefold())
        cleaned.append({
            "title": title[:300],
            "goal": str(item.get("goal") or "").strip()[:2000],
            "source_url": source_url[:1000],
        })
    if not cleaned:
        raise HTTPException(422, "Curriculum extraction produced no valid topics.")
    try:
        cid = execute(
            "INSERT INTO custom_courses(name,description,llm_model,schedule,mastery_threshold,source_policy,mode) VALUES(?,?,?,?,?,?,?)",
            (r.name.strip(), r.description.strip(), r.llm_model.strip(), r.schedule.strip() or "weekly",
             r.mastery_threshold, r.source_policy.strip() or "hybrid", r.mode.strip() or "auto"),
        )
        for order, item in enumerate(cleaned, 1):
            tid = execute(
                "INSERT INTO custom_course_topics(course_id,topic_order,title,goal,source_url) VALUES(?,?,?,?,?)",
                (cid, order, item["title"], item["goal"], item["source_url"] or None),
            )
            execute("INSERT INTO custom_course_progress(course_id,topic_id) VALUES(?,?)", (cid, tid))
    except Exception as exc:
        raise HTTPException(400, "Course could not be persisted.") from exc
    _ensure_custom_review_schedule(cid)
    audit(user, "learning", "write", "200", f"course-curriculum-extracted:{cid}:{len(cleaned)}")
    return {"id": cid, "status": "created", "topics": cleaned, "source_count": len(urls)}

@router.post("/settings/courses")
def create_course(r: CourseRequest, request: Request):
    user=require_admin(request); _setup()
    name=r.name.strip()
    if not name: raise HTTPException(400,"Course name is required.")
    try: cid=execute("INSERT INTO custom_courses(name,description,llm_model,schedule,mastery_threshold,source_policy,mode) VALUES(?,?,?,?,?,?,?)",
                    (name,r.description.strip(),r.llm_model.strip(),r.schedule.strip() or "weekly",r.mastery_threshold,r.source_policy.strip() or "hybrid",r.mode.strip() or "auto"))
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
        execute("UPDATE custom_courses SET name=?, description=?, llm_model=?, schedule=?, mastery_threshold=?, source_policy=?, mode=? WHERE id=?",
                 (name, r.description.strip(), r.llm_model.strip(), r.schedule.strip() or "weekly", r.mastery_threshold, r.source_policy.strip() or "hybrid", r.mode.strip() or "auto", course_id))
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

@router.post("/settings/courses/{course_id}/topics/{topic_id}/pause")
def course_topic_pause(course_id:int,topic_id:int,request:Request):
    user=require_admin(request); _setup()
    if not fetch_all("SELECT id FROM custom_course_topics WHERE id=? AND course_id=?",(topic_id,course_id)): raise HTTPException(404,"Topic not found.")
    _set_topic(topic_id,"paused",0,"paused")
    audit(user,"learning","topic-pause","200",f"{course_id}:{topic_id}")
    return {"status":"paused","topic_id":topic_id}

@router.post("/settings/courses/{course_id}/topics/{topic_id}/resume")
def course_topic_resume(course_id:int,topic_id:int,request:Request):
    user=require_admin(request); _setup()
    if not fetch_all("SELECT id FROM custom_course_topics WHERE id=? AND course_id=?",(topic_id,course_id)): raise HTTPException(404,"Topic not found.")
    _set_topic(topic_id,"planned",0,"planned")
    audit(user,"learning","topic-resume","200",f"{course_id}:{topic_id}")
    return {"status":"resumed","topic_id":topic_id}

@router.post("/settings/courses/{course_id}/topics/{topic_id}/reset")
def course_topic_reset(course_id:int,topic_id:int,request:Request):
    user=require_admin(request); _setup()
    if not fetch_all("SELECT id FROM custom_course_topics WHERE id=? AND course_id=?",(topic_id,course_id)): raise HTTPException(404,"Topic not found.")
    execute("UPDATE custom_course_progress SET status='planned',progress_percent=0,phase='planned',lesson=NULL,score=NULL,last_attempt_at=NULL,updated_at=CURRENT_TIMESTAMP WHERE topic_id=?",(topic_id,))
    audit(user,"learning","topic-reset","200",f"{course_id}:{topic_id}")
    return {"status":"reset","topic_id":topic_id}

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

@router.post("/settings/courses/{course_id}/resume")
def course_resume(course_id:int,request:Request):
    user=require_admin(request); _setup()
    if not _course(course_id): raise HTTPException(404,"Course not found.")
    execute("UPDATE custom_course_progress SET status='planned',phase='planned',updated_at=CURRENT_TIMESTAMP WHERE course_id=? AND status='paused'",(course_id,))
    if course_id not in _running: _workers.submit(_run_course,course_id)
    audit(user,"learning","resume","202",f"course-resume:{course_id}")
    return {"status":"resumed","course_id":course_id}

@router.post("/settings/courses/{course_id}/reset")
def course_reset(course_id:int,request:Request):
    user=require_admin(request); _setup()
    if not _course(course_id): raise HTTPException(404,"Course not found.")
    execute("UPDATE custom_course_progress SET status='planned',progress_percent=0,phase='planned',lesson=NULL,score=NULL,last_attempt_at=NULL,updated_at=CURRENT_TIMESTAMP WHERE course_id=?",(course_id,))
    audit(user,"learning","reset","200",f"course-reset:{course_id}")
    return {"status":"reset","course_id":course_id}

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

SETTINGS_HTML = """<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>تنظیمات | My-AI</title><style>body{font-family:Tahoma,system-ui;background:#f3f4f6;margin:0;color:#17202a}.wrap{max-width:1100px;margin:auto;padding:20px}.card{background:#fff;padding:18px;border-radius:14px;margin:12px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}input,textarea,select{width:100%;box-sizing:border-box;padding:10px;margin:5px 0;border:1px solid #ccc;border-radius:8px}button{padding:9px 14px;margin:3px;border:0;border-radius:8px;cursor:pointer}.bar{height:22px;background:#ddd;border-radius:8px;overflow:hidden}.fill{height:100%;background:#2563eb;color:#fff;text-align:center;line-height:22px;font-size:12px}.topic{border:1px solid #ddd;padding:9px;border-radius:9px;margin:6px 0}.muted{font-size:13px;color:#667085}.ok{background:#dcfce7}.warn{background:#fef3c7}.danger{background:#fee2e2}</style><style>body{background:linear-gradient(135deg,#eef2ff,#f8fafc 45%,#ecfeff)!important}.wrap{max-width:1220px!important}.card{border:1px solid #e5e7eb;box-shadow:0 8px 24px #0f172a0b!important;transition:.18s}.card:hover{box-shadow:0 12px 30px #0f172a12!important}.wrap>h1{background:linear-gradient(135deg,#111827,#1e3a8a);color:#fff;padding:24px;border-radius:20px}.grid{gap:16px!important}button{background:#1d4ed8;color:#fff!important;font-weight:700}button:hover{filter:brightness(1.05)}.topic{background:#f8fafc;border-color:#e2e8f0}.permissionGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:8px}.permGroup{background:#f8fafc;padding:10px;border-radius:10px;border:1px solid #e2e8f0}.mainMenu{position:sticky;top:10px;z-index:20;display:flex;gap:8px;flex-wrap:wrap;align-items:center;background:rgba(255,255,255,.94);backdrop-filter:blur(12px);padding:10px;border:1px solid #e5e7eb;border-radius:14px;box-shadow:0 8px 24px #0f172a12;margin:14px 0}.mainMenu a{padding:9px 12px;border-radius:10px;text-decoration:none;color:#1e3a8a;background:#eff6ff;font-weight:700}.mainMenu a:hover{background:#dbeafe}.moduleDashboard{grid-column:1/-1;background:linear-gradient(135deg,#ffffff,#f8fbff)}.moduleGrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}.moduleCard{background:#fff;border:1px solid #dbe4f0;border-radius:14px;padding:14px}.moduleCard summary{cursor:pointer;font-weight:800;color:#172554}.moduleFields{display:grid;gap:8px;margin-top:12px}.moduleFields label{font-size:13px;font-weight:700;color:#344054}.moduleFields input,.moduleFields textarea{margin:4px 0 0}.moduleActions{display:flex;gap:7px;flex-wrap:wrap;margin-top:8px}.moduleRecords{max-height:260px;overflow:auto;margin-top:8px}@media(max-width:700px){.wrap{padding:12px!important}.mainMenu{position:static}.moduleGrid{grid-template-columns:1fr}}</style><div class='wrap'><form id='settings-form' hidden></form><h1>تنظیمات My-AI</h1><nav class='mainMenu' aria-label='منوی اصلی'><a href='/'>خانه</a><a href='/settings'>تنظیمات</a><a href='#module-gui'>ماژول‌ها</a><a href='#provider'>Provider و Model</a><a href='#learning-sources'>منابع یادگیری</a><a href='#backup'>پشتیبان‌گیری</a><a href='#control-plane'>No-Code</a><a href='/learning'>مسیر یادگیری</a></nav><p class='muted'>دسترسی سریع به فرم‌های مدیریتی اصلی</p><div class='grid'><section class='card' id='provider'><h2>مدیریت Provider و Model</h2><p class='muted'>Provider و مدل را بدون ویرایش فایل تنظیمات مدیریت کن.</p><input id='pc_provider_id' type='hidden' value=''><input id='pc_name' placeholder='نام Provider'><input id='pc_protocol' value='openai-compatible' placeholder='Protocol'><input id='pc_endpoint' placeholder='Endpoint'><input id='pc_auth' value='none' placeholder='Auth type'><input id='pc_secret' type='password' autocomplete='new-password' placeholder='Secret / API key'><input id='pc_timeout' type='number' min='0.1' max='3600' step='0.1' value='30' placeholder='Timeout (seconds)'><input id='pc_capabilities' placeholder='Capabilities JSON, e.g. {"chat":true,"streaming":true}'><input id='pc_version' placeholder='Version'><label><input id='pc_enabled' type='checkbox' checked> فعال</label><button type='button' onclick='saveProviderCatalog()'>ذخیره Provider</button><div id='providers' class='topic'>در حال بارگذاری...</div><hr><input id='mc_provider' type='number' min='1' placeholder='Provider ID'><input id='mc_model' placeholder='Model ID'><input id='mc_tasks' placeholder='Tasks با , جدا شوند'><input id='mc_context' type='number' min='1' placeholder='Context length'><input id='mc_limits' placeholder='Limits JSON, e.g. {"input_tokens":8192}'><input id='mc_priority' type='number' min='0' value='100' placeholder='Priority'><input id='mc_version' placeholder='Version'><label><input id='mc_enabled' type='checkbox' checked> فعال</label><button type='button' onclick='saveModelCatalog()'>ذخیره Model</button><div id='models' class='topic'>در حال بارگذاری...</div><div id='catalogout' class='muted'></div></section><section class='card'><h2>Routing و Fallback مدل</h2><p class='muted'>مسیر انتخاب مدل و زنجیره fallback برای هر task را بدون تغییر کد مدیریت کنید.</p><input id='route_task' placeholder='Task مثل chat / coding / reasoning / embedding'><input id='route_model' placeholder='Model ID'><input id='route_provider' type='number' min='1' placeholder='Provider ID اختیاری'><input id='route_priority' type='number' min='0' value='100' placeholder='Priority'><button type='button' onclick='saveRoutingRuleGUI()'>ذخیره Routing Rule</button><input id='fallback_task' placeholder='Task fallback'><input id='fallback_models' placeholder='Model IDها با , جدا شوند'><button type='button' onclick='saveFallbackGUI()'>ذخیره Fallback Chain</button><div id='routingout' class='muted'></div><div id='routingitems' class='topic'>در حال بارگذاری...</div></section><section class='card' id='learning-sources'><h2>منابع یادگیری و Evidence</h2><input id='ls_url' placeholder='URL / file://'><input id='ls_type' value='custom' placeholder='نوع منبع'><input id='ls_product' placeholder='Product'><input id='ls_version' placeholder='Version'><input id='ls_priority' type='number' value='100' placeholder='Priority'><input id='ls_weight' type='number' min='0' step='0.1' value='1' placeholder='Weight'><button type='button' onclick='addLearningSourceCatalog()'>افزودن منبع</button><input id='ls_file' type='file'><button type='button' onclick='uploadLearningSourceCatalog()'>آپلود منبع</button><button type='button' onclick='loadLearningSourcesCatalog()'>بازخوانی</button><div id='learning-sources-catalog' class='topic'>در حال بارگذاری...</div></section><section class='card' id='backup'><h2>پشتیبان‌گیری و بازیابی</h2><input id='backup_path' placeholder='مسیر فایل backup'><button type='button' onclick='backupDatabaseGUI()'>Backup</button><button type='button' onclick='restoreDatabaseGUI()'>Restore</button><div id='backupout' class='muted'></div></section><section class='card' id='control-plane'><h2>مرکز مدیریت بدون کدنویسی</h2><p class='muted'>همان کنترل‌پلین مرکزی از GUI قابل مدیریت است و CLI نیز از همان persistence استفاده می‌کند.</p><select id='cp_namespace' onchange='loadControlPlane()'><option value=''>همه دسته‌ها</option></select><input id='cp_name' placeholder='نام مورد'><textarea id='cp_payload' rows='5' placeholder='JSON تنظیمات / policy / workflow'></textarea><label><input id='cp_enabled' type='checkbox' checked> فعال</label><br><button type='button' onclick='saveControlPlane()'>ذخیره / ویرایش</button><button type='button' onclick='loadControlPlane()'>بازخوانی</button><div id='controlplane' class='topic'>در حال بارگذاری...</div><div id='controlactions' class='topic'>تاریخچه عملیات...</div></section><section class='card'><h2>اتصال GitHub</h2><p class='muted'>هیچ Repository یا API URL پیش‌فرضی وجود ندارد. تنظیمات در دیتابیس نگهداری می‌شود؛ Token به‌صورت رمزنگاری‌شده ذخیره می‌شود. GitHub REST API با username/password احراز هویت نمی‌کند و برای API باید Token یا OAuth/CLI استفاده شود.</p><input id='apiurl' placeholder='GitHub API URL'><input id='repo' placeholder='owner/repository'><input id='ghuser' placeholder='GitHub username (اختیاری)'><input id='token' type='password' form='settings-form' autocomplete='new-password' placeholder='Personal Access Token'><button onclick='saveGithubConfig()'>ثبت تنظیمات GitHub</button><button onclick='saveToken()'>ثبت Token</button><button onclick='checkGit()'>بررسی اتصال</button><button onclick='loginGit()'>ورود با GitHub CLI/OAuth</button><button onclick='logoutGit()'>خروج</button><div id='gitout' class='muted'></div></section>
<section class='card'><h2>Self-Update</h2><label><input id='su_enabled' type='checkbox'> فعال‌سازی Self-Update برای بررسی و اجرای به‌روزرسانی خودکار</label><label><input id='su_approved' type='checkbox'> اجازه اجرای Update بدون تأیید دستی در مرحله اجرا</label><input id='su_health' placeholder='Health URL محلی، مثلاً http://127.0.0.1:8000/health'><button onclick='saveFeatures()'>ذخیره</button><div id='suout' class='muted'></div></section>
<section class='card'><h2>Self-Repair</h2><label><input id='sr_enabled' type='checkbox'> فعال‌سازی Self-Repair برای پیشنهاد/اجرای تعمیرات</label><label><input id='sr_approval' type='checkbox' checked> قبل از اعمال تعمیر، تأیید ادمین الزامی باشد</label><button onclick='saveFeatures()'>ذخیره</button><div id='srout' class='muted'></div></section>
<section class='card'><h2>یادگیری سریع</h2><label><input id='lf_enabled' type='checkbox'> فعال</label><input id='lf_interval' type='number' min='60' max='86400' placeholder='فاصله یادگیری (ثانیه)'><input id='lf_retries' type='number' min='1' max='20' placeholder='حداکثر تلاش منبع'><button onclick='saveFeatures()'>ذخیره</button><div id='lfout' class='muted'></div></section><section class='card'><h2>تولید تصویر کاملاً آفلاین</h2><p class='muted'>فقط Automatic1111 روی همین کامپیوتر استفاده می‌شود و این مسیر هیچ API ابری ندارد. برای کیفیت بالا، checkpoint مناسب Manga/Anime/SDXL را در Automatic1111 نصب کنید.</p><label><input id='img_enabled' type='checkbox'> فعال</label><input id='img_url' placeholder='http://127.0.0.1:7860'><input id='img_model' placeholder='نام checkpoint/مدل نصب‌شده'><input id='img_sampler' placeholder='DPM++ 2M Karras'><div class='grid'><label>Steps<input id='img_steps' type='number' min='1' max='150'></label><label>CFG<input id='img_cfg' type='number' min='1' max='30' step='0.1'></label><label>اندازه<input id='img_size' placeholder='1024x1024'></label><label>Hires Scale<input id='img_hires_scale' type='number' min='1' max='2' step='0.1'></label><label>Denoise<input id='img_denoise' type='number' min='0.1' max='1' step='0.05'></label><input id='img_upscaler' placeholder='Latent'></div><label><input id='img_hires' type='checkbox'> Hires Fix</label><textarea id='img_negative' rows='5' placeholder='Negative prompt پیش‌فرض'></textarea><button onclick='saveImageSettings()'>ذخیره تنظیمات تصویر</button><button onclick='checkImageEngine()'>بررسی موتور محلی</button><div id='imgout' class='muted'></div></section><section class='card'><h2>لاگ‌های کنسول</h2><p class='muted'>حداقل سطح لاگ‌هایی که در کنسول نمایش داده می‌شوند را انتخاب کنید. تغییر این گزینه بدون ری‌استارت اعمال می‌شود.</p><select id='log_level'><option value='DEBUG'>Debug — همه جزئیات</option><option value='INFO'>Info — اطلاعات و هشدارها</option><option value='WARNING'>Warning — هشدار و خطا</option><option value='ERROR'>Error — فقط خطاها</option><option value='CRITICAL'>Critical — فقط خطاهای بحرانی</option></select><button onclick='saveLogging()'>ذخیره تنظیمات لاگ</button><div id='logout' class='muted'></div></section><section class='card'><h2>منابع سخت‌افزاری</h2><p class='muted'>سقف پیش‌فرض اجرای یادگیری: CPU برابر 70٪ با 8 thread، RAM برابر 80٪ و GPU برابر 0 لایه (فقط CPU). این مقادیر قابل تغییر هستند.</p><label>حداکثر CPU (%)<input id='cpu_percent' type='number' min='1' max='100' step='0.5'></label><label>تعداد CPU thread<input id='cpu_threads' type='number' min='1' max='128' step='1'></label><label>حداکثر RAM (%)<input id='ram_percent' type='number' min='1' max='100' step='0.5'></label><label>GPU layers (0 = فقط CPU)<input id='gpu_layers' type='number' min='0' max='128' step='1'></label><button onclick='saveResources()'>ذخیره منابع</button><div id='resourceout' class='muted'></div></section><section class='card'><h2>Configuration Registry</h2><p class='muted'>تنظیمات ثبت‌شده، مقدار فعلی و پیش‌فرض را نشان می‌دهد و امکان بازنشانی امن فراهم است.</p><button type='button' onclick='exportRegistry()'>خروجی تنظیمات</button> <input id='registry-search' placeholder='جستجوی تنظیمات...' oninput='filterRegistry(this.value)' style='max-width:260px'> <button type='button' onclick='document.getElementById("registry-file").click()'>ورود تنظیمات</button><input id='registry-file' type='file' accept='application/json' style='display:none' onchange='importRegistryFile(this.files[0])'><div id='settings-registry'>در حال بارگذاری...</div><div id='registryout' class='muted'></div></section><section class='card'><h2>مرکز عملیات گرافیکی</h2><p class='muted'>عملیات قابل اجرای سریع را بدون نوشتن command از اینجا انجام بده. عملیات حساس همچنان permission و audit خود را حفظ می‌کنند.</p><div id='ui-actions'>در حال بارگذاری...</div></section><section class='card'><h2>پنل عملیات مدیریتی</h2><p class='muted'>معادل گرافیکی عملیات مدیریتی CLI.</p><button type='button' onclick='adminGUI("status")'>وضعیت</button><button type='button' onclick='adminGUI("health")'>سلامت</button><button type='button' onclick='adminGUI("sessions")'>Sessionها</button><button type='button' onclick='adminGUI("memory")'>Memory</button><button type='button' onclick='adminGUI("tools")'>Tools</button><button type='button' onclick='adminGUI("policies")'>Policies</button><button type='button' onclick='adminGUI("learning")'>Learning</button><button type='button' onclick='adminGUI("repairs")'>Repairs</button><button type='button' onclick='adminGUI("rollback")'>Rollback</button><button type='button' onclick='adminGUI("diagnostics")'>Diagnostics</button><pre id='adminguiout' class='topic'></pre></section><section class='card'><h2>پروفایل‌های پیکربندی</h2><p class='muted'>ذخیره و فعال‌سازی مجموعه تنظیمات بدون ویرایش فایل.</p><input id='profile_name' placeholder='نام پروفایل'><textarea id='profile_settings' rows='6' placeholder='JSON settings'></textarea><label><input id='profile_activate' type='checkbox'> فعال‌سازی</label><button type='button' onclick='saveProfileGUI()'>ذخیره پروفایل</button><button type='button' onclick='loadProfilesGUI()'>بارگذاری</button><div id='profiles' class='topic'></div><div id='profileout' class='muted'></div></section><section class='card moduleDashboard' id='module-gui'><h2>داشبورد ماژول‌ها</h2><p class='muted'>فرم‌های مدرن ماژول‌ها از منوی اصلی در دسترس هستند. هر کارت وضعیت، تنظیمات و رکوردهای همان ماژول را مدیریت می‌کند.</p><div id='module-gui-list' class='moduleGrid'>در حال بارگذاری ماژول‌ها...</div><div id='module-gui-out' class='muted'></div></section><section class='card'><h2>مدیریت یکپارچه No-Code</h2><p class='muted'>مدیریت مشترک Agent، Tool، Memory، Research، Security، Scheduler، Execution، Integration، Observability، Database، Prompt/Policy و Evaluation.</p><select id='cp_namespace'></select><input id='cp_name' placeholder='نام رکورد'><textarea id='cp_payload' rows='8' placeholder='JSON payload'></textarea><label><input id='cp_enabled' type='checkbox' checked> فعال</label><button type='button' onclick='loadControlNamespacesGUI()'>بارگذاری</button><button type='button' onclick='saveControlRecordGUI()'>ذخیره</button><div id='cp_records' class='topic'></div><div id='cp_out' class='muted'></div><hr><h3>چرخه عملیات</h3><input id='cp_action' placeholder='نام عملیات'><input id='cp_target' placeholder='شناسه هدف اختیاری'><button type='button' onclick='startControlActionGUI()'>شروع عملیات</button><input id='cp_action_id' placeholder='شناسه عملیات'><select id='cp_action_status'><option value='started'>started</option><option value='running'>running</option><option value='paused'>paused</option><option value='completed'>completed</option><option value='failed'>failed</option><option value='cancelled'>cancelled</option></select><input id='cp_action_progress' type='number' min='0' max='100' value='0' placeholder='درصد پیشرفت'><textarea id='cp_action_result' rows='3' placeholder='JSON result'></textarea><input id='cp_action_error' placeholder='خطا در صورت وجود'><button type='button' onclick='loadControlActionGUI(byId("cp_action_id").value)'>مشاهده وضعیت</button><button type='button' onclick='updateControlActionGUI()'>به‌روزرسانی عملیات</button><div id='cp_action_out' class='muted'></div></section><section class='card'><h2>Registryهای Agent و Plugin</h2><div><input id='prompt_name' placeholder='نام Prompt'><input id='prompt_task' placeholder='task'><textarea id='prompt_text' rows='4' placeholder='متن Prompt'></textarea><button type='button' onclick='savePromptGUI()'>انتشار Prompt</button><button type='button' onclick='activatePromptGUI()'>فعال‌سازی Prompt</button></div><div><input id='policy_name' placeholder='نام Policy'><textarea id='policy_payload' rows='4' placeholder='JSON policy'></textarea><button type='button' onclick='savePolicyGUI()'>انتشار Policy</button></div><div><input id='plugin_name' placeholder='نام Plugin'><input id='plugin_source' placeholder='منبع'><input id='plugin_version' placeholder='نسخه'><input id='plugin_caps' placeholder='capabilities با کاما'><button type='button' onclick='proposePluginGUI()'>ثبت پیشنهاد Plugin</button><button type='button' onclick='approvePluginGUI()'>تأیید Plugin</button><button type='button' onclick='rejectPluginGUI()'>رد Plugin</button></div><div id='registry_agent_out' class='muted'></div></section><section class='card'><h2>مدیریت کاربران</h2><div id='users'>در حال بارگذاری...</div><hr><input id='nu' autocomplete='username' placeholder='نام کاربری'><input id='np' type='password' form='settings-form' autocomplete='new-password' placeholder='رمز عبور حداقل ۱۰ کاراکتر'><input id='nd' placeholder='نام نمایشی'><button onclick='addUser()'>ایجاد کاربر</button><div id='userout' class='muted'></div></section></div>
<section class='card'><h2>مجوز ابزار کاربران</h2><p class='muted'>برای هر کاربر، ابزار و نوع عملیات را مشخص کنید. عدم وجود مجوز یعنی Deny.</p><div id='permissions'>در حال بارگذاری...</div></section><section class='card'><h2>افزودن Topic به آموزش موجود</h2><p class='muted'>Topic جدید با وضعیت «برنامه‌ریزی‌شده» اضافه می‌شود و درصد کلی آموزش دوباره محاسبه خواهد شد.</p><input id='existing_course_id' type='number' min='1' placeholder='شناسه آموزش'><input id='existing_topic' placeholder='عنوان Topic جدید'><input id='existing_goal' placeholder='هدف Topic'><input id='existing_source' placeholder='آدرس منبع رسمی اختیاری'><button onclick='addCourseTopic()'>افزودن Topic</button><div id='courseout' class='muted'></div></section><section class='card'><h2>ساخت آموزش جدید</h2><p class='muted'>هر خط یک سرفصل: <code>عنوان | هدف | آدرس منبع رسمی اختیاری</code>. می‌توانی هر موضوع دلخواهی بسازی.</p><input id='cn' placeholder='نام آموزش، مثلاً Python'><input id='cd' placeholder='توضیح آموزش'><input id='course_llm' placeholder='LLM مدل (اختیاری)'><input id='course_schedule' value='weekly' placeholder='Schedule'><input id='course_mastery' type='number' min='0' max='1' step='0.05' value='0.8' placeholder='Mastery threshold'><select id='course_source_policy'><option value='hybrid'>ترکیبی</option><option value='manual-first'>منبع دستی اولویت دارد</option><option value='auto-first'>کشف خودکار اولویت دارد</option></select><select id='course_mode'><option value='auto'>Auto Discover</option><option value='manual'>Manual Sources</option><option value='hybrid'>Hybrid</option></select><textarea id='ct' rows='12' placeholder='Python functions | توابع و پارامترها | https://docs.python.org/3/tutorial/'></textarea><button onclick='createCourse()'>ایجاد آموزش</button><div id='newcourseout' class='muted'></div></section></div><script src='/settings/script.js?v=20260923-3'></script><script>
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
    except RuntimeError as exc:
        logging.getLogger(__name__).debug("learning worker shutdown already completed: %s", exc)

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

