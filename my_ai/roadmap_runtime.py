"""Persistent services covering the advanced architecture roadmap.

The module is additive: it uses dedicated tables and never rewrites existing
knowledge, conversation, or backup records.
"""
from __future__ import annotations

import json
import os
import platform
import time
from dataclasses import asdict
from typing import Any, Callable

from .advanced_agent import (
    Capability, ModelProfile, ModelRouter, ResourceScheduler, ResourceSnapshot,
    RuntimeMode, TaskProfile,
)
from .db import execute, fetch_all
from .config import settings


def runtime_mode() -> RuntimeMode:
    raw = os.getenv("MYAI_RUNTIME_MODE", "local").strip().lower()
    return RuntimeMode(raw) if raw in {x.value for x in RuntimeMode} else RuntimeMode.LOCAL


def resource_snapshot() -> ResourceSnapshot:
    try:
        import psutil
        mem = psutil.virtual_memory()
        return ResourceSnapshot(mem.available / 1024**3, 0.0, float(psutil.cpu_percent(interval=None)))
    except Exception:
        return ResourceSnapshot(0.0, 0.0, 0.0)


def model_catalog() -> list[ModelProfile]:
    configured = [
        ("router", os.getenv("ROUTER_MODEL", settings.ollama_model), 0.55, 0.8),
        ("coding", os.getenv("CODING_MODEL", settings.ollama_model), 0.8, 0.65),
        ("fallback", os.getenv("FALLBACK_MODEL", settings.ollama_model), 0.45, 0.85),
    ]
    try:
        profiles = json.loads(os.getenv("MYAI_MODEL_PROFILES", "{}"))
    except json.JSONDecodeError:
        profiles = {}
    result: list[ModelProfile] = []
    for role, name, quality, speed in configured:
        name = str(name or "").strip()
        if not name:
            continue
        profile = profiles.get(name) if isinstance(profiles, dict) else {}
        if not isinstance(profile, dict):
            profile = {}
        capabilities = set(profile.get("capabilities") or {"chat"})
        if role == "coding":
            capabilities.add("code")
        result.append(ModelProfile(
            name,
            int(str(profile.get("context_window") or os.getenv("OLLAMA_NUM_CTX", "8192"))),
            ram_gb=float(profile.get("ram_gb") or 0.0),
            vram_gb=float(profile.get("vram_gb") or 0.0),
            quality=float(profile.get("quality") or quality),
            speed=float(profile.get("speed") or speed),
            capabilities=frozenset(map(str, capabilities)),
        ))
    return result


def choose_model(task: TaskProfile) -> dict[str, Any]:
    models = model_catalog()
    resources = resource_snapshot()
    if not models:
        raise RuntimeError("no configured models")
    try:
        choice = ModelRouter().choose(models, task, resources)
        return {"model": asdict(choice.model), "reason": choice.reason, "fallback": False, "resources": asdict(resources)}
    except RuntimeError as exc:
        viable = [
            m for m in models
            if task.required_capabilities <= m.capabilities
            and m.ram_gb <= resources.ram_available_gb
            and m.vram_gb <= resources.vram_available_gb
        ]
        fallback = max(viable, key=lambda m: (m.context_window, m.quality, m.speed), default=None)
        if fallback is None:
            raise
        return {
            "model": asdict(fallback),
            "reason": f"fallback: {exc}; context capped to {fallback.context_window}",
            "fallback": True,
            "resources": asdict(resources),
        }


_scheduler = ResourceScheduler(max_concurrent=max(1, int(os.getenv("MYAI_MAX_CONCURRENT", "1"))))


def acquire_resource() -> bool:
    return _scheduler.acquire()


def release_resource() -> None:
    _scheduler.release()


def register_capability(cap: Capability) -> None:
    execute(
        """INSERT INTO agent_capabilities(name,risk,enabled,requires_approval,offline)
           VALUES(?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET risk=excluded.risk,
           enabled=excluded.enabled,requires_approval=excluded.requires_approval,offline=excluded.offline""",
        (cap.name, cap.risk.value, int(cap.enabled), int(cap.requires_approval), int(cap.offline)),
    )


def capabilities() -> list[dict[str, Any]]:
    return fetch_all("SELECT * FROM agent_capabilities ORDER BY name")


def authorize_capability(name: str, *, approved: bool = False, mode: RuntimeMode | None = None) -> None:
    mode = mode or runtime_mode()
    rows = fetch_all("SELECT * FROM agent_capabilities WHERE name=?", (name,))
    if not rows or not rows[0]["enabled"]:
        raise PermissionError(f"capability disabled: {name}")
    cap = rows[0]
    if cap["requires_approval"] and not approved:
        raise PermissionError(f"approval required: {name}")
    if mode is RuntimeMode.ONLINE and not cap["offline"] and not approved:
        raise PermissionError(f"approval required for online capability: {name}")


def upsert_knowledge_version(knowledge_id: int, content: str, source_url: str | None = None, confidence: float | None = None) -> dict[str, Any]:
    rows = fetch_all("SELECT COALESCE(MAX(version),0) AS version FROM knowledge_versions WHERE knowledge_id=?", (knowledge_id,))
    version = int(rows[0]["version"]) + 1
    execute("UPDATE knowledge_versions SET status='superseded' WHERE knowledge_id=? AND status='active'", (knowledge_id,))
    vid = execute("INSERT INTO knowledge_versions(knowledge_id,version,content,source_url,confidence,status) VALUES(?,?,?,?,?,'active')", (knowledge_id,version,content,source_url,confidence))
    return {"id": vid, "knowledge_id": knowledge_id, "version": version, "status": "active"}


def knowledge_versions(knowledge_id: int) -> list[dict[str, Any]]:
    return fetch_all("SELECT * FROM knowledge_versions WHERE knowledge_id=? ORDER BY version DESC", (knowledge_id,))


def record_conflict(claim_key: str, left_version_id: int, right_version_id: int) -> int:
    return execute("INSERT INTO knowledge_conflicts(claim_key,left_version_id,right_version_id) VALUES(?,?,?)", (claim_key,left_version_id,right_version_id))


def resolve_conflict(conflict_id: int, resolved_version_id: int, resolution: str) -> int:
    execute("UPDATE knowledge_conflicts SET status='resolved',resolved_version_id=?,resolution=? WHERE id=?", (resolved_version_id,resolution,conflict_id))
    return conflict_id


def evidence_node(node_key: str, kind: str, value: str, metadata: dict[str, Any] | None = None) -> int:
    existing = fetch_all("SELECT id FROM evidence_nodes WHERE node_key=?", (node_key,))
    if existing:
        return int(existing[0]["id"])
    return execute("INSERT INTO evidence_nodes(node_key,kind,value,metadata) VALUES(?,?,?,?)", (node_key,kind,value,json.dumps(metadata or {},ensure_ascii=False)))


def evidence_edge(source_key: str, relation: str, target_key: str) -> None:
    source = fetch_all("SELECT id FROM evidence_nodes WHERE node_key=?", (source_key,))
    target = fetch_all("SELECT id FROM evidence_nodes WHERE node_key=?", (target_key,))
    if not source or not target:
        raise KeyError("evidence edge requires existing nodes")
    execute("INSERT OR IGNORE INTO evidence_edges(source_id,relation,target_id) VALUES(?,?,?)", (source[0]["id"],relation,target[0]["id"]))


def trace(session_id: int | None, run_id: int | None, node_key: str, kind: str, value: str, metadata: dict[str, Any] | None = None) -> int:
    return execute("INSERT INTO agent_traces(session_id,run_id,node_key,kind,value,metadata) VALUES(?,?,?,?,?,?)", (session_id,run_id,node_key,kind,value,json.dumps(metadata or {},ensure_ascii=False)))


def completion_report(goal: str, requirements: list[str], validation: list[str], unresolved: list[str] | None = None) -> dict[str, Any]:
    unresolved = unresolved or []
    return {"goal": goal, "requirements": requirements, "validation": validation, "unresolved": unresolved, "complete": bool(goal and requirements and validation and not unresolved)}


def benchmark_case(suite: str, case_name: str, input_text: str, expected: str, evaluator: Callable[[str], Any]) -> dict[str, Any]:
    started = time.monotonic()
    try:
        actual = str(evaluator(input_text))
        passed = actual == expected
        detail = "" if passed else f"expected={expected!r} actual={actual!r}"
    except Exception as exc:
        actual, passed, detail = "", False, f"{type(exc).__name__}: {exc}"
    latency = int((time.monotonic() - started) * 1000)
    bid = execute("INSERT INTO agent_benchmarks(suite,case_name,input,expected,actual,passed,latency_ms,details) VALUES(?,?,?,?,?,?,?,?)", (suite,case_name,input_text,expected,actual,int(passed),latency,detail))
    return {"id": bid, "suite": suite, "case": case_name, "passed": passed, "latency_ms": latency, "details": detail}


def benchmark_summary(suite: str | None = None) -> dict[str, Any]:
    if suite:
        rows = fetch_all("SELECT * FROM agent_benchmarks WHERE suite=? ORDER BY id DESC", (suite,))
    else:
        rows = fetch_all("SELECT * FROM agent_benchmarks ORDER BY id DESC")
    return {"total": len(rows), "passed": sum(int(r["passed"]) for r in rows), "failed": sum(1-int(r["passed"]) for r in rows), "cases": rows[:100]}


def maintenance(limit: int = 100) -> dict[str, Any]:
    rows = fetch_all("SELECT id,verification_status,verified_at FROM knowledge ORDER BY id DESC LIMIT ?", (max(1,min(limit,500)),))
    checked = 0
    for row in rows:
        status = "fresh" if row["verification_status"] == "verified" and row["verified_at"] else "review"
        execute("INSERT INTO knowledge_maintenance(knowledge_id,action,status,details) VALUES(?,?,?,?)", (row["id"],"scheduled_review",status,"deterministic freshness check"))
        checked += 1
    return {"checked": checked, "review_required": sum(1 for r in rows if not (r["verification_status"] == "verified" and r["verified_at"]))}


def add_memory_lesson(category: str, lesson: str, source: str, regression_case: str | None = None) -> int:
    return execute("INSERT INTO learning_lessons(category,lesson,source,regression_case) VALUES(?,?,?,?)", (category,lesson,source,regression_case))


def lessons(category: str | None = None) -> list[dict[str, Any]]:
    return fetch_all("SELECT * FROM learning_lessons WHERE (? IS NULL OR category=?) ORDER BY id DESC", (category,category))


def add_research_trace(requirement: str, query: str, source: str, finding: str, decision: str = "", artifact: str = "", validation: str = "") -> int:
    return execute("INSERT INTO research_trace(requirement,query,source,finding,decision,artifact,validation) VALUES(?,?,?,?,?,?,?)", (requirement,query,source,finding,decision,artifact,validation))


def research_trace_rows(requirement: str | None = None) -> list[dict[str, Any]]:
    return fetch_all("SELECT * FROM research_trace WHERE (? IS NULL OR requirement=?) ORDER BY id DESC", (requirement,requirement))


def system_profile() -> dict[str, Any]:
    return {"platform": platform.platform(), "python": platform.python_version(), "mode": runtime_mode().value, "models": [asdict(x) for x in model_catalog()], "resources": asdict(resource_snapshot()), "max_concurrent": _scheduler.max_concurrent}
