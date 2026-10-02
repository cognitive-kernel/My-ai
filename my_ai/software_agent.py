import logging\nlogger = logging.getLogger(__name__)\nfrom __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .db import execute, search_knowledge
from .infra.llm import create_llm
from .web_learner import WebLearner
from .project_builder import build_project


PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["goal", "language", "framework", "requirements", "architecture", "phases", "acceptance_criteria", "research_queries", "validation"],
    "properties": {
        "goal": {"type": "string"},
        "language": {"type": ["string", "null"]},
        "framework": {"type": ["string", "null"]},
        "requirements": {"type": "array", "items": {"type": "string"}, "maxItems": 40},
        "architecture": {"type": "array", "items": {"type": "string"}, "maxItems": 30},
        "phases": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 30},
        "acceptance_criteria": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 40},
        "research_queries": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
        "validation": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
    },
}


@dataclass
class ResearchBundle:
    sources: list[dict[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_prompt(self) -> str:
        payload = {"sources": self.sources[-12:], "notes": self.notes[-20:]}
        return json.dumps(payload, ensure_ascii=False)[:24000]


@dataclass
class SoftwareTask:
    request: str
    plan: dict[str, Any]
    research: ResearchBundle


def _safe_text(value: Any, limit: int = 5000) -> str:
    return str(value or "").strip()[:limit]


def _plan(request: str, context: str = "") -> dict[str, Any]:
    llm = create_llm("coding")
    prompt = (
        "Analyze the software request as a senior product owner and software architect. "
        "Infer intent from meaning, not trigger words. Preserve explicit user constraints and use conversation context only to resolve references. "
        "Choose a language/framework only when justified by the request; otherwise leave it null so implementation can choose. "
        "Return only JSON matching the schema. Include concrete acceptance criteria that can be tested locally.\n"
        f"CURRENT REQUEST:\n{request}\nCONTEXT:\n{context[:12000]}"
    )
    data = llm.structured_chat_json(prompt, PLAN_SCHEMA, system="You are My-AI's software planning agent. Do not write code yet.")
    if not isinstance(data, dict):
        raise ValueError("Planner returned an invalid plan.")
    return data


def _research(plan: dict[str, Any]) -> ResearchBundle:
    bundle = ResearchBundle()
    local_query = " ".join([_safe_text(plan.get("language")), _safe_text(plan.get("framework")), _safe_text(plan.get("goal"))])
    for item in search_knowledge(local_query, 12):
        bundle.sources.append({
            "title": _safe_text(item.get("title"), 300),
            "url": _safe_text(item.get("source_url") or item.get("url") or "local://knowledge"),
            "summary": _safe_text(item.get("content"), 1200),
        })

    learner = WebLearner()
    for query in list(plan.get("research_queries") or [])[:8]:
        try:
            results = learner.search(_safe_text(query, 500), limit=5)
        except Exception as exc:
            bundle.notes.append(f"Research search failed for {query!r}: {exc}")
            continue
        for result in results:
            url = _safe_text(result.get("url"), 1000)
            if not url:
                continue
            source = {"title": _safe_text(result.get("title"), 300), "url": url, "summary": ""}
            try:
                title, text = learner.fetch(url)
                source["title"] = _safe_text(title, 300)
                source["summary"] = _safe_text(text, 1800)
            except Exception as exc:
                source["summary"] = f"Fetch unavailable: {exc}"
            bundle.sources.append(source)
            if len(bundle.sources) >= 24:
                break
        if len(bundle.sources) >= 24:
            break

    # Keep the research auditable without making it a new source of executable instructions.
    try:
        execute(
            "CREATE TABLE IF NOT EXISTS software_research (id INTEGER PRIMARY KEY AUTOINCREMENT, goal TEXT NOT NULL, plan_json TEXT NOT NULL, sources_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        execute(
            "INSERT INTO software_research(goal,plan_json,sources_json) VALUES(?,?,?)",
            (_safe_text(plan.get("goal"), 10000), json.dumps(plan, ensure_ascii=False), json.dumps(bundle.sources, ensure_ascii=False)),
        )
    except Exception as exc:
        logger.warning("SOFTWARE_AGENT_PERSISTENCE_FAILED: %s", exc)
    return bundle


def _git_snapshot(workspace: Path) -> dict[str, Any]:
    if not (workspace / ".git").exists():
        return {"initialized": False, "status": "not-a-git-repository"}
    try:
        status = subprocess.run(["git", "status", "--porcelain"], cwd=workspace, capture_output=True, text=True, timeout=30)
        return {"initialized": True, "dirty": bool(status.stdout.strip()), "status": status.stdout[-12000:]}
    except Exception as exc:
        return {"initialized": True, "error": str(exc)}


def _ensure_git_commit(workspace: Path, message: str) -> dict[str, Any]:
    try:
        if not (workspace / ".git").exists():
            init = subprocess.run(["git", "init"], cwd=workspace, capture_output=True, text=True, timeout=30)
            if init.returncode:
                return {"ok": False, "error": init.stderr or init.stdout}
        add = subprocess.run(["git", "add", "-A"], cwd=workspace, capture_output=True, text=True, timeout=30)
        if add.returncode:
            return {"ok": False, "error": add.stderr or add.stdout}
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=workspace, capture_output=True, text=True, timeout=30)
        if diff.returncode == 0:
            return {"ok": True, "committed": False, "status": _git_snapshot(workspace)}
        commit = subprocess.run(["git", "-c", "user.name=My-AI", "-c", "user.email=my-ai@localhost", "commit", "-m", message], cwd=workspace, capture_output=True, text=True, timeout=60)
        if commit.returncode:
            return {"ok": False, "error": commit.stderr or commit.stdout}
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=workspace, capture_output=True, text=True, timeout=30)
        return {"ok": True, "committed": True, "commit": head.stdout.strip(), "status": _git_snapshot(workspace)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_software_task(
    request: str,
    *,
    language: str | None = None,
    project_path: str | None = None,
    context: str = "",
    timeout: int = 300,
    repair_attempts: int = 3,
) -> dict[str, Any]:
    request = _safe_text(request, 20000)
    if not request:
        raise ValueError("Software request is required.")

    plan = _plan(request, context)
    if language:
        plan["language"] = language
    research = _research(plan)
    enriched_request = (
        "SOFTWARE ENGINEERING PLAN:\n" + json.dumps(plan, ensure_ascii=False)[:20000]
        + "\n\nRESEARCH BUNDLE:\n" + research.as_prompt()
        + "\n\nUSER REQUEST:\n" + request
    )
    result = build_project(
        enriched_request,
        str(plan.get("language") or language or "Python"),
        project_path=project_path,
        timeout=timeout,
        repair_attempts=repair_attempts,
    )
    result["plan"] = plan
    result["research"] = {"source_count": len(research.sources), "sources": research.sources}
    workspace_value = result.get("project_path") or result.get("workspace")
    if workspace_value:
        workspace = Path(str(workspace_value)).resolve()
        result["git"] = _ensure_git_commit(workspace, "feat: complete generated project")
    else:
        result["git"] = {"ok": False, "error": "Project workspace was not returned."}

    # A generated artifact is not automatically a completed task.
    build_ok = bool((result.get("build") or {}).get("passed"))
    tests_ok = bool((result.get("tests") or {}).get("passed"))
    lint_ok = bool((result.get("lint") or {}).get("passed"))
    git_ok = bool((result.get("git") or {}).get("ok"))
    result["completion"] = {
        "plan": True,
        "build": build_ok,
        "tests": tests_ok,
        "lint": lint_ok,
        "git": git_ok,
        "completed": bool(result.get("status") == "built" and build_ok and tests_ok and lint_ok and git_ok),
    }
    return result
