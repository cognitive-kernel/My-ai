from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .db import execute, search_knowledge
from .infra.llm import create_llm
from .web_learner import WebLearner
from .project_builder import build_project
from .software_validation import validate_plan


PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["goal", "artifact_type", "language", "framework", "requirements", "tool_requirements", "architecture", "phases", "acceptance_criteria", "research_queries", "validation", "constraints", "ambiguities"],
    "properties": {
        "goal": {"type": "string"},
        "artifact_type": {"type": "string"},
        "language": {"type": ["string", "null"]},
        "framework": {"type": ["string", "null"]},
        "requirements": {"type": "array", "items": {"type": "string"}, "maxItems": 40},
        "tool_requirements": {
            "type": "array",
            "maxItems": 40,
            "items": {
                "type": "object"
            },
        },
        "architecture": {"type": "array", "items": {"type": "string"}, "maxItems": 30},
        "phases": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 30},
        "acceptance_criteria": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 40},
        "research_queries": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
        "validation": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
        "constraints": {"type": "array", "items": {"type": "string"}, "maxItems": 30},
        "ambiguities": {"type": "array", "items": {"type": "string"}, "maxItems": 20},
    },
}


@dataclass
class ResearchBundle:
    sources: list[dict[str, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_prompt(self) -> str:
        payload = {"sources": self.sources[-16:], "notes": self.notes[-20:]}
        return json.dumps(payload, ensure_ascii=False)[:30000]


@dataclass
class SoftwareTask:
    request: str
    plan: dict[str, Any]
    research: ResearchBundle


def _safe_text(value: Any, limit: int = 5000) -> str:
    return str(value or "").strip()[:limit]


def _explicit_language(request: str, context: str = "") -> str | None:
    """Semantically identify a language only when the user explicitly names one."""
    llm = create_llm("coding")
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["explicit", "language"],
        "properties": {
            "explicit": {"type": "boolean"},
            "language": {"type": ["string", "null"]},
        },
    }
    prompt = (
        "Determine whether the software request explicitly names a programming language. "
        "Use semantic meaning, not a hard-coded language list. If a language is explicitly named, return its conventional name exactly enough to preserve the user's constraint. "
        "Do not infer a language from the artifact type, platform, framework, tools, or examples. "
        "Return null when no programming language is explicitly requested. Return only JSON matching the schema.\\n"
        f"REQUEST:\\n{request}\\nCONTEXT:\\n{context[:12000]}"
    )
    data = llm.structured_chat_json(prompt, schema, system="You extract explicit software constraints semantically.")
    if not isinstance(data, dict) or not data.get("explicit"):
        return None
    value = str(data.get("language") or "").strip()
    return value or None


def _plan(request: str, context: str = "") -> dict[str, Any]:
    llm = create_llm("coding")
    prompt = (
        "Semantically analyze the software request and preserve explicit user constraints. Do not rely on trigger words or phrase lists. Identify the artifact type before choosing technology. "
        "If a programming language is explicitly named, preserve it; otherwise language may be null. "
        "For MT4, distinguish indicators from Expert Advisors; trade execution or broad terminal/account/chart access belongs in an EA. Never mix MQL5 APIs into MQL4. If trading is requested without a strategy, make trading explicitly user-controlled and do not invent entry logic. "
        "Translate the plan into lifecycle host-tool requirements for build/test/lint/run only. Do not model application behavior as host tools. Use provider alternatives when multiple host tools can provide the same capability; each provider must be one coherent tool family with real executable names and provider-specific lifecycle commands. Prefer host-discoverable alternatives instead of assuming a particular compiler. Installation metadata may contain only trusted manager/package identifiers. Never emit URLs, arbitrary installer commands, shell commands, artifact names, or synthetic executables. "
        "Every acceptance criterion must be testable. Return only JSON matching the schema. Do not write code yet.\n"
        f"CURRENT REQUEST:\n{request}\nCONTEXT:\n{context[:16000]}"
    )
    data = llm.structured_chat_json(prompt, PLAN_SCHEMA, system="You are My-AI's semantic software planning and research-planning agent. Never invent platform capabilities.")
    if not isinstance(data, dict):
        raise ValueError("Planner returned an invalid plan.")
    if not str(data.get("language") or "").strip():
        explicit_language = _explicit_language(request, context)
        if explicit_language:
            data["language"] = explicit_language
    validate_plan(data)
    return data


def _research(plan: dict[str, Any]) -> ResearchBundle:
    bundle = ResearchBundle()
    local_query = " ".join([_safe_text(plan.get("language")), _safe_text(plan.get("framework")), _safe_text(plan.get("artifact_type")), _safe_text(plan.get("goal"))])
    for item in search_knowledge(local_query, 16):
        bundle.sources.append({
            "title": _safe_text(item.get("title"), 300),
            "url": _safe_text(item.get("source_url") or item.get("url") or "local://knowledge"),
            "summary": _safe_text(item.get("content"), 1600),
        })

    learner = WebLearner()
    for query in list(plan.get("research_queries") or [])[:10]:
        try:
            results = learner.search(_safe_text(query, 700), limit=6)
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
                source["summary"] = _safe_text(text, 2200)
            except Exception as exc:
                source["summary"] = f"Fetch unavailable: {exc}"
            bundle.sources.append(source)
            if len(bundle.sources) >= 32:
                break
        if len(bundle.sources) >= 32:
            break

    try:
        execute("CREATE TABLE IF NOT EXISTS software_research (id INTEGER PRIMARY KEY AUTOINCREMENT, goal TEXT NOT NULL, plan_json TEXT NOT NULL, sources_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        execute("INSERT INTO software_research(goal,plan_json,sources_json) VALUES(?,?,?)", (_safe_text(plan.get("goal"), 10000), json.dumps(plan, ensure_ascii=False), json.dumps(bundle.sources, ensure_ascii=False)))
    except Exception:
        pass
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



_SELF_REVIEW_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["passed", "criteria", "defects", "notes"],
    "properties": {
        "passed": {"type": "boolean"},
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["criterion", "passed", "evidence"],
                "properties": {
                    "criterion": {"type": "string"},
                    "passed": {"type": "boolean"},
                    "evidence": {"type": "string"},
                },
            },
            "maxItems": 40,
        },
        "defects": {"type": "array", "items": {"type": "string"}, "maxItems": 40},
        "notes": {"type": "array", "items": {"type": "string"}, "maxItems": 40},
    },
}


def _self_review(plan: dict[str, Any], result: dict[str, Any], workspace: Path | None) -> dict[str, Any]:
    """Review the generated artifact against the plan using only observable evidence."""
    if workspace is None or not workspace.exists():
        return {"passed": False, "criteria": [], "defects": ["Generated workspace is unavailable."], "notes": []}

    evidence = {
        "plan": {
            "goal": plan.get("goal"),
            "artifact_type": plan.get("artifact_type"),
            "requirements": plan.get("requirements"),
            "acceptance_criteria": plan.get("acceptance_criteria"),
            "constraints": plan.get("constraints"),
        },
        "validation": {
            "build": result.get("build"),
            "tests": result.get("tests"),
            "lint": result.get("lint"),
            "run": result.get("run"),
            "semantic_defects": result.get("semantic_defects") or [],
        },
        "artifacts": result.get("artifacts") or result.get("files") or [],
        "git_status": _git_snapshot(workspace),
    }
    prompt = (
        "Perform a strict evidence-based self-review of the generated software artifact. "
        "Evaluate every acceptance criterion from the plan. A criterion may be marked passed only when the supplied evidence actually demonstrates it; "
        "do not infer successful execution, browser behavior, APIs, or capabilities that are not evidenced. "
        "If evidence is missing or contradictory, mark the criterion failed and explain what is missing. "
        "Do not invent requirements. Unresolved semantic defects are failures. "
        "Return only JSON matching the schema.\n\n"
        + json.dumps(evidence, ensure_ascii=False)[:30000]
    )
    try:
        review = create_llm("coding").structured_chat_json(
            prompt,
            _SELF_REVIEW_SCHEMA,
            system="You are a strict software acceptance reviewer. Evidence outranks assumptions.",
        )
    except Exception as exc:
        return {"passed": False, "criteria": [], "defects": [f"Self-review failed: {exc}"], "notes": []}
    if not isinstance(review, dict):
        return {"passed": False, "criteria": [], "defects": ["Self-review returned invalid data."], "notes": []}

    criteria = review.get("criteria") if isinstance(review.get("criteria"), list) else []
    expected = [str(x).strip() for x in plan.get("acceptance_criteria") or [] if str(x).strip()]
    normalized = {str(x.get("criterion") or "").strip(): x for x in criteria if isinstance(x, dict)}
    missing = [criterion for criterion in expected if criterion not in normalized]
    failed = [criterion for criterion in expected if criterion in normalized and not bool(normalized[criterion].get("passed"))]
    defects = [str(x).strip() for x in review.get("defects") or [] if str(x).strip()]
    if missing:
        defects.append("Self-review did not evaluate every acceptance criterion: " + "; ".join(missing))
    if failed:
        defects.append("Acceptance criteria failed: " + "; ".join(failed))
    passed = not defects and len(criteria) >= len(expected) and bool(review.get("passed"))
    return {**review, "passed": passed, "defects": defects}



def run_software_task(request: str, *, language: str | None = None, project_path: str | None = None, context: str = "", timeout: int = 300, repair_attempts: int = 3) -> dict[str, Any]:
    request = _safe_text(request, 20000)
    if not request:
        raise ValueError("Software request is required.")

    plan = _plan(request, context)
    if language:
        plan["language"] = language
    research = _research(plan)
    enriched_request = (
        "SOFTWARE ENGINEERING PLAN:\n" + json.dumps(plan, ensure_ascii=False)[:26000]
        + "\n\nRESEARCH BUNDLE:\n" + research.as_prompt()
        + "\n\nUSER REQUEST:\n" + request
    )
    result = build_project(enriched_request, str(plan.get("language") or language or ""), project_path=project_path, timeout=timeout, repair_attempts=repair_attempts, tool_requirements=plan.get("tool_requirements"))
    result["plan"] = plan
    result["research"] = {"source_count": len(research.sources), "sources": research.sources}
    workspace_value = result.get("project_path") or result.get("workspace")
    workspace = Path(str(workspace_value)).resolve() if workspace_value else None

    build_ok = bool((result.get("build") or {}).get("passed"))
    tests_ok = bool((result.get("tests") or {}).get("passed"))
    lint_ok = bool((result.get("lint") or {}).get("passed"))
    runtime_ok = bool((result.get("run") or {}).get("passed"))
    research_required = bool(plan.get("research_queries"))
    research_ok = bool(research.sources) if research_required else True

    review = _self_review(plan, result, workspace)
    result["self_review"] = review

    # Never commit an incomplete artifact as "complete".
    pre_commit_ok = bool(
        result.get("status") == "built"
        and build_ok and tests_ok and lint_ok and runtime_ok
        and research_ok and not result.get("semantic_defects")
        and bool(review.get("passed"))
        and workspace is not None
    )
    if pre_commit_ok:
        result["git"] = _ensure_git_commit(workspace, "feat: complete generated project")
    elif workspace is not None:
        result["git"] = {"ok": False, "committed": False, "status": _git_snapshot(workspace), "reason": "Completion prerequisites were not satisfied; workspace was not committed."}
    else:
        result["git"] = {"ok": False, "committed": False, "error": "Project workspace was not returned."}

    git_ok = bool((result.get("git") or {}).get("ok"))
    result["completion"] = {
        "plan": True,
        "research": research_ok,
        "build": build_ok,
        "tests": tests_ok,
        "lint": lint_ok,
        "runtime": runtime_ok,
        "self_review": bool(review.get("passed")),
        "git": git_ok,
        "completed": bool(pre_commit_ok and git_ok),
    }
    return result
