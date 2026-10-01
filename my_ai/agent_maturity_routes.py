from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from .db import fetch_all
from .agent_maturity import (
    config_version,
    config_versions,
    create_task,
    create_task_workspace,
    get_task,
    memory_lifecycle,
    memory_lifecycle_rows,
    maturity_summary,
    register_tool_manifest,
    task_trace,
    tool_manifests,
    transition_task,
    save_config_version,
)


def register_maturity_routes(app, require_user) -> None:
    router = APIRouter(prefix="/roadmap/maturity", tags=["agent-maturity"], dependencies=[Depends(require_user)])

    @router.get("/summary")
    async def summary():
        return maturity_summary()

    @router.post("/tasks")
    async def task_create(request: Request):
        data = await request.json()
        return create_task(str(data.get("goal", "")), data.get("session_id"), data.get("metadata"))

    @router.get("/tasks")
    async def task_list(state: str | None = None, limit: int = 100):
        if state:
            return {"items": fetch_all("SELECT * FROM agent_tasks WHERE state=? ORDER BY id DESC LIMIT ?", (state, max(1, min(limit, 500))))}
        return {"items": fetch_all("SELECT * FROM agent_tasks ORDER BY id DESC LIMIT ?", (max(1, min(limit, 500)),))}

    @router.get("/tasks/{task_id}")
    async def task_get(task_id: int):
        return get_task(task_id)

    @router.post("/tasks/{task_id}/transition")
    async def task_transition(task_id: int, request: Request):
        data = await request.json()
        return transition_task(task_id, str(data.get("state", "")), str(data.get("event", "transition")), data.get("payload"))

    @router.get("/tasks/{task_id}/trace")
    async def task_trace_get(task_id: int, limit: int = 200):
        return {"items": task_trace(task_id, limit)}

    @router.post("/tasks/{task_id}/workspace")
    async def task_workspace_create(task_id: int, request: Request):
        data = await request.json()
        path = create_task_workspace(task_id, str(data.get("project_name", "task")))
        return {"task_id": task_id, "path": str(path)}

    @router.get("/memory")
    async def memory_get(limit: int = 100):
        return {"items": memory_lifecycle_rows(limit)}

    @router.post("/memory/{knowledge_id}/lifecycle")
    async def memory_transition(knowledge_id: int, request: Request):
        data = await request.json()
        return memory_lifecycle(knowledge_id, str(data.get("status", "")))

    @router.get("/tools")
    async def tools_get():
        return {"items": tool_manifests()}

    @router.post("/tools")
    async def tools_register(request: Request):
        return register_tool_manifest(await request.json())

    @router.get("/config")
    async def config_get():
        return {"items": config_versions()}

    @router.get("/config/{version}")
    async def config_get_one(version: str):
        return config_version(version)

    @router.post("/config")
    async def config_add(request: Request):
        data = await request.json()
        return {"version": str(data["version"]), "config": save_config_version(str(data["version"]), data.get("config") or {}, bool(data.get("activate", False)))}

    @router.get("/ui")
    async def maturity_ui():
        return """<!doctype html><html lang="fa" dir="rtl"><meta charset="utf-8"><title>My-AI Agent Operations</title>
        <style>body{font-family:system-ui;max-width:1100px;margin:30px auto;padding:20px}section{padding:16px;margin:12px 0;border:1px solid #ddd;border-radius:12px}pre{white-space:pre-wrap;overflow:auto}</style>
        <h1>Agent Operations</h1><section><h2>Summary</h2><pre id="summary">loading...</pre></section>
        <section><h2>Tasks</h2><pre id="tasks">loading...</pre></section><section><h2>Tools</h2><pre id="tools">loading...</pre></section>
        <section><h2>Configuration</h2><pre id="config">loading...</pre></section>
        <script>
        Promise.all([
          fetch('/roadmap/maturity/summary').then(r=>r.json()),
          fetch('/roadmap/maturity/tasks').then(r=>r.json()),
          fetch('/roadmap/maturity/tools').then(r=>r.json()),
          fetch('/roadmap/maturity/config').then(r=>r.json())
        ]).then(([s,t,toolsData,c])=>{summary.textContent=JSON.stringify(s,null,2);tasks.textContent=JSON.stringify(t,null,2);tools.textContent=JSON.stringify(toolsData,null,2);config.textContent=JSON.stringify(c,null,2)})
        .catch(e=>summary.textContent=String(e));
        </script></html>"""

    app.include_router(router)
