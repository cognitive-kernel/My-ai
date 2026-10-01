from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request

from .advanced_agent import Capability, OperationRisk, RuntimeMode, TaskProfile
from .personal_benchmark import validate_suite
from .db import execute, fetch_all
from .roadmap_runtime import (
    add_memory_lesson, add_research_trace, authorize_capability, benchmark_summary, benchmark_model_selection,
    capabilities, choose_model, completion_report, evidence_edge, evidence_node,
    knowledge_versions, lessons, maintenance, model_catalog, register_capability,
    resource_snapshot, research_trace_rows, resolve_conflict, record_conflict, model_management,
    system_profile, trace, upsert_knowledge_version,
)


def register_roadmap_routes(app, require_user) -> None:
    router = APIRouter(prefix="/roadmap", tags=["roadmap"], dependencies=[Depends(require_user)])

    @router.get("/profile")
    async def profile():
        return system_profile()

    @router.get("/models")
    async def models():
        return {"models": [{**m.__dict__, "capabilities": sorted(m.capabilities)} for m in model_catalog()]}

    @router.post("/models/select")
    async def model_select(request: Request):
        data = await request.json()
        task = TaskProfile(
            complexity=float(data.get("complexity", 0.5)),
            context_tokens=max(1, int(data.get("context_tokens", 4096))),
            latency_budget_ms=max(1, int(data.get("latency_budget_ms", 30000))),
            required_capabilities=frozenset(map(str, data.get("required_capabilities") or [])),
            network_allowed=bool(data.get("network_allowed", False)),
        )
        return choose_model(task)

    @router.get("/models/management")
    async def models_management():
        return model_management()

    @router.get("/models/benchmark")
    async def models_benchmark():
        return benchmark_model_selection()

    @router.get("/resources")
    async def resources():
        return resource_snapshot().__dict__

    @router.get("/capabilities")
    async def capability_list():
        return {"items": capabilities()}

    @router.post("/capabilities")
    async def capability_add(request: Request):
        data = await request.json()
        risk = OperationRisk(str(data.get("risk", "read")))
        cap = Capability(
            str(data["name"]), risk, bool(data.get("enabled", True)),
            bool(data.get("requires_approval", False)), bool(data.get("offline", True))
        )
        register_capability(cap)
        execute(
            "UPDATE agent_capabilities SET platform_constraints=?,validation=?,fallback=? WHERE name=?",
            (
                json.dumps(data.get("platform_constraints") or {}, ensure_ascii=False),
                str(data.get("validation") or ""),
                str(data.get("fallback") or ""),
                cap.name,
            ),
        )
        return {"ok": True, "name": cap.name}

    @router.post("/capabilities/authorize")
    async def capability_authorize(request: Request):
        data = await request.json()
        mode_raw = str(data.get("mode", "local"))
        mode = RuntimeMode(mode_raw) if mode_raw in {x.value for x in RuntimeMode} else RuntimeMode.LOCAL
        authorize_capability(str(data["name"]), approved=bool(data.get("approved", False)), mode=mode)
        return {"authorized": True}

    @router.get("/knowledge")
    async def knowledge_list(query: str | None = None, category: str | None = None, limit: int = 50):
        needle = f"%{str(query or '').strip()}%"
        rows = fetch_all(
            """SELECT id,topic,title,content,source_url,category,verification_status,verified_at,confidence,created_at
               FROM knowledge
               WHERE (?='' OR title LIKE ? OR topic LIKE ? OR content LIKE ?)
                 AND (? IS NULL OR category=?)
               ORDER BY id DESC LIMIT ?""",
            (str(query or "").strip(), needle, needle, needle, category, category, max(1, min(limit, 200))),
        )
        return {"items": rows}

    @router.post("/knowledge/{knowledge_id}/archive")
    async def knowledge_archive(knowledge_id: int):
        execute("UPDATE knowledge SET verification_status='archived' WHERE id=?", (knowledge_id,))
        return {"archived": True, "id": knowledge_id}

    @router.get("/knowledge/{knowledge_id}/retrieval")
    async def knowledge_retrieval(knowledge_id: int):
        return {"items": fetch_all("SELECT * FROM retrieval_judgments WHERE knowledge_id=? ORDER BY id DESC LIMIT 100", (knowledge_id,))}

    @router.post("/knowledge/{knowledge_id}/versions")
    async def knowledge_version(knowledge_id: int, request: Request):
        data = await request.json()
        return upsert_knowledge_version(knowledge_id, str(data.get("content", "")), data.get("source_url"), data.get("confidence"))

    @router.get("/knowledge/{knowledge_id}/versions")
    async def knowledge_version_history(knowledge_id: int):
        return {"items": knowledge_versions(knowledge_id)}

    @router.post("/knowledge/conflicts")
    async def knowledge_conflict(request: Request):
        data = await request.json()
        return {"id": record_conflict(str(data["claim_key"]), int(data["left_version_id"]), int(data["right_version_id"]))}

    @router.get("/knowledge/conflicts/{conflict_id}")
    async def knowledge_conflict_detail(conflict_id: int):
        rows = fetch_all(
            """SELECT c.*, lv.version AS left_version, lv.content AS left_content, lv.source_url AS left_source, lv.confidence AS left_confidence,
                      rv.version AS right_version, rv.content AS right_content, rv.source_url AS right_source, rv.confidence AS right_confidence
               FROM knowledge_conflicts c
               JOIN knowledge_versions lv ON lv.id=c.left_version_id
               JOIN knowledge_versions rv ON rv.id=c.right_version_id
               WHERE c.id=?""",
            (conflict_id,),
        )
        return {"item": rows[0] if rows else None}

    @router.post("/knowledge/conflicts/{conflict_id}/resolve")
    async def knowledge_conflict_resolve(conflict_id: int, request: Request):
        data = await request.json()
        return {"updated": resolve_conflict(conflict_id, int(data["resolved_version_id"]), str(data.get("resolution", "")))}

    @router.post("/evidence/node")
    async def evidence_add(request: Request):
        data = await request.json()
        return {"id": evidence_node(str(data["node_key"]), str(data["kind"]), str(data["value"]), data.get("metadata"))}

    @router.post("/evidence/edge")
    async def evidence_link(request: Request):
        data = await request.json()
        evidence_edge(str(data["source_key"]), str(data["relation"]), str(data["target_key"]))
        return {"ok": True}

    @router.post("/trace")
    async def trace_add(request: Request):
        data = await request.json()
        return {"id": trace(data.get("session_id"), data.get("run_id"), str(data["node_key"]), str(data["kind"]), str(data["value"]), data.get("metadata"))}

    @router.get("/maintenance")
    async def maintenance_run(limit: int = 100):
        return maintenance(limit)

    @router.post("/lessons")
    async def lesson_add(request: Request):
        data = await request.json()
        return {"id": add_memory_lesson(str(data["category"]), str(data["lesson"]), str(data["source"]), data.get("regression_case"))}

    @router.get("/lessons")
    async def lesson_list(category: str | None = None):
        return {"items": lessons(category)}
\n    @router.post("/lessons/{lesson_id}/lifecycle")
    async def lesson_lifecycle(lesson_id: int, request: Request):
        data = await request.json()
        status = str(data.get("status", "validated"))
        if status not in {"candidate", "validated", "retired"}:
            raise ValueError("invalid lesson lifecycle status")
        execute("UPDATE learning_lessons SET status=? WHERE id=?", (status, lesson_id))
        return {"id": lesson_id, "status": status}


    @router.post("/research-trace")
    async def research_add(request: Request):
        data = await request.json()
        return {"id": add_research_trace(str(data["requirement"]), str(data["query"]), str(data["source"]), str(data["finding"]), str(data.get("decision", "")), str(data.get("artifact", "")), str(data.get("validation", "")))}

    @router.get("/research-trace")
    async def research_list(requirement: str | None = None):
        return {"items": research_trace_rows(requirement)}

    @router.post("/completion")
    async def completion(request: Request):
        data = await request.json()
        return completion_report(
            str(data.get("goal", "")),
            [str(x) for x in data.get("requirements") or []],
            [str(x) for x in data.get("validation") or []],
            [str(x) for x in data.get("unresolved") or []],
            [str(x) for x in data.get("artifacts") or []],
            [str(x) for x in data.get("research") or []],
            [str(x) for x in data.get("limitations") or []],
        )

    @router.get("/benchmarks")
    async def benchmarks(suite: str | None = None):
        return benchmark_summary(suite)

    @router.get("/benchmarks/suite")
    async def benchmark_suite():
        return validate_suite()

    @router.get("/knowledge-ui")
    async def knowledge_ui():
        return """<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><title>My-AI Knowledge Management</title>
        <body style="font-family:system-ui;max-width:1000px;margin:40px auto;padding:20px">
        <h1>مدیریت دانش</h1><p>نسخه‌ها، conflictها، provenance و maintenance بدون حذف خودکار داده نمایش داده می‌شوند.</p>
        <pre id="out">در حال بارگذاری...</pre>
        <script>
        Promise.all([fetch('/roadmap/knowledge').then(r=>r.json()),fetch('/roadmap/lessons').then(r=>r.json()),fetch('/roadmap/research-trace').then(r=>r.json())])
        .then(x=>document.getElementById('out').textContent=JSON.stringify({knowledge:x[0],lessons:x[1],research:x[2]},null,2))
        .catch(e=>document.getElementById('out').textContent=String(e));
        </script></body></html>"""

    @router.get("/model-ui")
    async def model_ui():
        return """<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><title>My-AI Model Management</title>
        <body style="font-family:system-ui;max-width:1000px;margin:40px auto;padding:20px"><h1>مدیریت مدل</h1>
        <pre id="out">در حال بارگذاری...</pre>
        <script>Promise.all([fetch('/roadmap/models/management').then(r=>r.json()),fetch('/roadmap/models/benchmark').then(r=>r.json()),fetch('/roadmap/resources').then(r=>r.json())]).then(x=>document.getElementById('out').textContent=JSON.stringify({models:x[0],resources:x[1]},null,2));</script></body></html>"""
    app.include_router(router)
