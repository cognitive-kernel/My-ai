# mypy: ignore-errors
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .config import assert_write_allowed
from .curriculum import canonical_language
from .db import execute, fetch_all, search_knowledge
from .llm import create_llm
from .project_workspace import create_project_workspace, resolve_projects_root
from .tooling import run_project_tool, doctor
from .software_validation import validate_generated_project, validate_validation_matrix

ROOT = Path(__file__).resolve().parent.parent
MAX_FILES = 80
MAX_FILE_CHARS = 200_000
MAX_CONTEXT_CHARS = 45_000


def _clean_path(value: str) -> str:
    raw = str(value or "").replace("\\", "/").strip().lstrip("/")
    p = Path(raw)
    if not raw or raw.startswith("~") or any(part in {"..", "."} for part in p.parts):
        raise ValueError("Invalid project file path.")
    if len(raw) > 180 or raw.startswith(".git/"):
        raise ValueError("Invalid project file path.")
    return raw


def _strip_fence(text: str) -> str:
    value = str(text or "").strip()
    fence = chr(96) * 3
    if value.startswith(fence):
        value = value[len(fence):].lstrip()
        if value.startswith("json"):
            value = value[4:].lstrip()
        if value.endswith(fence):
            value = value[:-len(fence)].rstrip()
    return value


def _repair_json_string_escapes(text: str) -> str:
    """Escape invalid backslashes inside JSON strings without changing valid escapes."""
    valid = {"\\\"", "\\\\", "\\/", "\\b", "\\f", "\\n", "\\r", "\\t", "\\u"}
    out: list[str] = []
    in_string = False
    escaped = False
    i = 0
    while i < len(text):
        ch = text[i]
        if not in_string:
            out.append(ch)
            if ch == '\"':
                in_string = True
            i += 1
            continue
        if escaped:
            out.append(ch)
            escaped = False
            i += 1
            continue
        if ch == "\\":
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if nxt and ("\\\\" + nxt) in valid:
                out.append(ch)
            else:
                out.append("\\\\\\\\")
            escaped = True if nxt and ("\\\\" + nxt) in valid else False
            i += 1
            continue
        out.append(ch)
        if ch == '\"':
            in_string = False
        i += 1
    return "".join(out)


def _parse_files(raw: str) -> dict[str, str]:
    payload = _strip_fence(raw)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        if "Invalid \\escape" not in str(exc):
            raise
        data = json.loads(_repair_json_string_escapes(payload))
    if isinstance(data, dict) and isinstance(data.get("files"), dict):
        data = data["files"]
    if not isinstance(data, dict):
        raise ValueError("Project generator did not return a files object.")
    result = {}
    for key, content in data.items():
        path = _clean_path(str(key))
        if len(result) >= MAX_FILES:
            raise ValueError("Generated project contains too many files.")
        text = str(content if content is not None else "")
        if len(text) > MAX_FILE_CHARS:
            raise ValueError(f"Generated file is too large: {path}")
        result[path] = text
    if not result:
        raise ValueError("Generated project contains no files.")
    return result


def _write_files(workspace: Path, files: dict[str, str]) -> list[str]:
    assert_write_allowed(str(workspace))
    root = workspace.resolve()
    written = []
    for relative, content in files.items():
        target = (root / relative).resolve()
        target.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(str(target.relative_to(root)).replace("\\", "/"))
    return written


def _run(language: str, operation: str, workspace: Path, timeout: int, tool_requirements: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    try:
        return run_project_tool(language, operation, str(workspace), timeout, requirements=tool_requirements)
    except Exception as exc:
        return {"language": canonical_language(language), "operation": operation, "passed": False, "return_code": -1, "output": "", "error": str(exc)}

def _has_lifecycle_command(requirements: list[dict[str, Any]] | None, operation: str) -> bool:
    for item in requirements or []:
        if not isinstance(item, dict):
            continue
        commands = item.get("commands")
        value = item.get(operation)
        if value is None and isinstance(commands, dict):
            value = commands.get(operation)
        if isinstance(value, str) and value.strip():
            return True
        if isinstance(value, list) and any(str(x).strip() for x in value):
            return True
    return False


def _recent_conversation_context(goal: str) -> tuple[str, str | None, int | None]:
    sessions = fetch_all("SELECT id,language FROM chat_sessions WHERE kind='chat' ORDER BY updated_at DESC,id DESC LIMIT 1")
    if not sessions:
        return goal, None, None
    session_id = int(sessions[0]["id"])
    rows = fetch_all("SELECT role,content FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT 80", (session_id,))[::-1]
    current = str(goal or "").strip()
    current_language = None
    conversation_context = "\n".join(
        f"{row['role']}: {str(row['content'] or '')[:7000]}" for row in rows[-20:]
    )[:MAX_CONTEXT_CHARS]
    language = current_language or sessions[0].get("language")
    resolved_goal = current
    if conversation_context:
        resolved_goal += "\n\nFULL CHAT CONTEXT FOR THIS PROJECT REQUEST:\n" + conversation_context
    return resolved_goal, language, session_id
_FAILURE_DIAGNOSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["category", "cause", "repair_strategy", "research_needed"],
    "properties": {
        "category": {"type": "string"},
        "cause": {"type": "string"},
        "repair_strategy": {"type": "string"},
        "research_needed": {"type": "boolean"},
    },
}


def _diagnose_failure(llm: Any, operation: str, evidence: str) -> dict[str, Any]:
    """Classify observable validation evidence to guide the next repair attempt."""
    fallback = {
        "category": "unknown",
        "cause": "Validation failed without a structured diagnosis.",
        "repair_strategy": "Reinspect the generated artifact and the reported validation evidence.",
        "research_needed": False,
    }
    try:
        data = llm.structured_chat_json(
            "Diagnose the software validation failure from observable evidence only. "
            "Do not claim that a repair was performed. Do not invent missing facts. "
            "Choose a concise category such as requirements, dependency, environment, "
            "implementation, test, platform, or unknown. Return only JSON matching the schema.\n"
            f"OPERATION: {operation}\nEVIDENCE:\n{str(evidence or '')[:18000]}",
            _FAILURE_DIAGNOSIS_SCHEMA,
            system="You diagnose software engineering failures for the next repair attempt.",
        )
        if not isinstance(data, dict):
            return fallback
        category = str(data.get("category") or "").strip()
        cause = str(data.get("cause") or "").strip()
        strategy = str(data.get("repair_strategy") or "").strip()
        if not category or not cause or not strategy:
            return fallback
        return {
            "category": category,
            "cause": cause,
            "repair_strategy": strategy,
            "research_needed": bool(data.get("research_needed")),
        }
    except Exception:
        return fallback


def _prompt(language: str, goal: str, knowledge: list[Any], previous_error: str = "", diagnosis: dict[str, Any] | None = None) -> str:
    suffix = f"\nPREVIOUS VALIDATION/BUILD/TEST/LINT DEFECTS (fix every one; do not merely explain them):\n{previous_error[:18000]}" if previous_error else ""
    if diagnosis:
        suffix += f"\nSTRUCTURED FAILURE DIAGNOSIS (guidance only; validation remains authoritative):\n{json.dumps(diagnosis, ensure_ascii=False)[:6000]}"
    return (
        "Generate a complete runnable software project, not a single source file. Return ONLY valid JSON: {\"files\":{\"relative/path\":\"file contents\"}}. "
        "The embedded software plan and research are authoritative design inputs, but independently check their consistency. "
        "Never mix incompatible platform APIs. Never invent a missing business rule or use an unconditional placeholder to simulate one. "
        "If the requested artifact type cannot legally or technically perform a requested capability, implement the closest valid architecture described by the plan and document the boundary. "
        "The conversation context is authoritative for follow-up requests; ignore previous assistant answers when they conflict with the user's own requirements. "
        "Create all necessary source files, dependency manifests, configuration, tests, and README build/run instructions. Use the selected language/framework and keep paths relative to the project root. "
        "Do not use absolute paths, secrets, runtime network downloads, or placeholder TODO implementations. "
        f"LANGUAGE: {language}\nGOAL AND PLAN/RESEARCH: {goal}\nLEARNED KNOWLEDGE: {json.dumps(knowledge, ensure_ascii=False)[:32000]}{suffix}"
    )


def _artifact_files(workspace: Path) -> list[str]:
    roots = ("dist", "build", "target", "bin", "out", "app/build/outputs")
    out = []
    for rel in roots:
        base = workspace / rel
        if base.exists():
            out.extend(str(p.relative_to(workspace)).replace("\\", "/") for p in base.rglob("*") if p.is_file())
    return out[:200]


def _supported_language(value: str | None) -> str | None:
    candidate = canonical_language(str(value or "").strip())
    # Do not collapse an unknown/new language to a hard-coded fallback.
    # The semantic planner selects the implementation language; build/validation
    # layers decide later whether a local toolchain exists.
    return candidate or None

def _plan_language(goal: str) -> str | None:
    try:
        marker = "SOFTWARE ENGINEERING PLAN:\n"
        if marker not in goal:
            return None
        payload = goal.split(marker, 1)[1].split("\n\nRESEARCH BUNDLE:", 1)[0]
        return _supported_language(json.loads(payload).get("language"))
    except Exception:
        return None


def _phase_workspace_context(workspace: Path, limit: int = 16000) -> str:
    chunks: list[str] = []
    used = 0
    for path in sorted(workspace.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        remaining = limit - used
        if remaining <= 0:
            break
        snippet = text[:min(3000, remaining)]
        chunks.append(f"FILE: {path.relative_to(workspace).as_posix()}\n{snippet}")
        used += len(snippet)
    return "\n\n".join(chunks)


def _generate_phase(llm: Any, language: str, goal: str, phase: str, workspace: Path, knowledge: list[Any]) -> dict[str, Any]:
    prompt = (
        "Implement one phase of an existing software project incrementally. "
        "Preserve valid existing files. Return only new or changed files as JSON "
        "with a top-level files object. Do not invent requirements, use placeholders, "
        "or replace working functionality unrelated to this phase.\n"
        f"LANGUAGE: {language}\nPHASE: {phase}\nPLAN: {goal}\n"
        f"CURRENT WORKSPACE:\n{_phase_workspace_context(workspace)}\n"
        f"RESEARCH:\n{json.dumps(knowledge, ensure_ascii=False)[:10000]}"
    )
    return _parse_files(llm.chat(prompt, system="You are an incremental software implementation engineer. Work phase-by-phase and preserve the existing workspace."))



def build_project(goal: str, language: str = "", *, project_path: str | None = None, timeout: int = 300, repair_attempts: int = 2, tool_requirements: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    goal = str(goal or "").strip()
    if not goal:
        raise ValueError("Project goal is required.")
    resolved_goal, contextual_language, session_id = _recent_conversation_context(goal)
    detected_language = contextual_language
    language = _plan_language(resolved_goal) or _supported_language(detected_language) or _supported_language(language) or ""
    # A supplied project_path identifies the target workspace itself. Do not create
    # a new child directory: modify_artifact requests must operate on that project.
    workspace = resolve_projects_root(project_path) if project_path else create_project_workspace(goal)
    knowledge = search_knowledge(language + " " + resolved_goal, 20)
    llm = create_llm("coding")
    files = {}
    phase_validation: list[dict[str, Any]] = []
    build = tests = lint = typecheck = run = {}
    last_error = ""
    last_diagnosis: dict[str, Any] | None = None
    attempts = max(1, min(int(repair_attempts) + 1, 5))
    semantic_defects: list[str] = []
    requirements = tool_requirements
    plan_data: dict[str, Any] = {}
    try:
        marker = "SOFTWARE ENGINEERING PLAN:\n"
        if marker in resolved_goal:
            plan_text = resolved_goal.split(marker, 1)[1].split("\n\nRESEARCH BUNDLE:", 1)[0]
            candidate = json.loads(plan_text)
            if isinstance(candidate, dict):
                plan_data = candidate
    except Exception:
        plan_data = {}
    try:
        research_marker = "RESEARCH BUNDLE:\n"
        if research_marker in resolved_goal:
            research_text = resolved_goal.split(research_marker, 1)[1].split("\n\nUSER REQUEST:", 1)[0]
            research_data = json.loads(research_text)
            if isinstance(research_data, dict):
                research_path = workspace / ".myai" / "research.json"
                research_path.parent.mkdir(parents=True, exist_ok=True)
                research_path.write_text(json.dumps(research_data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    phased = False
    if plan_data:
        matrix_defects = validate_validation_matrix(plan_data, language)
        if matrix_defects:
            return {
                "status": "build_failed", "language": language, "request": resolved_goal,
                "project_path": str(workspace.relative_to(ROOT)) if workspace.is_relative_to(ROOT) else str(workspace),
                "files": [], "file_count": 0, "build": {}, "tests": {}, "lint": {}, "typecheck": {}, "run": {},
                "semantic_defects": matrix_defects, "phase_validation": [], "repair_attempts": 0,
                "failure_diagnosis": {"category": "validation_plan", "cause": "; ".join(matrix_defects),
                "repair_strategy": "Declare the required validation commands in the semantic plan.", "research_needed": False},
                "artifacts": [], "toolchain": doctor(language, cwd=str(workspace), requirements=requirements or []),
            }
        phases = [str(item).strip() for item in (plan_data.get("phases") or []) if str(item).strip()]
        phased = len(phases) > 1
        if phased:
            skeleton_prompt = (
                "Create only the runnable project skeleton. Include manifest, configuration, entrypoint, "
                "test scaffold and required directories, but do not implement business features. Return only JSON "
                "with a top-level files object.\nLANGUAGE: " + language + "\nPLAN: " + resolved_goal
            )
            skeleton_files = _parse_files(llm.chat(skeleton_prompt, system="You create minimal runnable software skeletons."))
            written = _write_files(workspace, skeleton_files)
            defects = validate_generated_project(workspace, plan_data, language)
            phase_validation.append({"phase": 0, "name": "skeleton", "files": written, "passed": not bool(defects), "defects": defects})
            if defects:
                semantic_defects = defects
                last_error = "\n".join(defects)
                last_diagnosis = _diagnose_failure(llm, "skeleton_validation", last_error)
            else:
                for index, phase in enumerate(phases, 1):
                    phase_files = _generate_phase(llm, language, resolved_goal, phase, workspace, knowledge)
                    written = _write_files(workspace, phase_files)
                    defects = validate_generated_project(workspace, plan_data, language)
                    phase_validation.append({"phase": index, "name": phase, "files": written, "passed": not bool(defects), "defects": defects})
                    if defects:
                        semantic_defects = defects
                        last_error = "\n".join(defects)
                        last_diagnosis = _diagnose_failure(llm, "phase_validation", last_error)
                        break
    if not phased:
        for _ in range(attempts):
            files = _parse_files(llm.chat(_prompt(language, resolved_goal, knowledge, last_error, last_diagnosis), system="You are a senior software architect and implementation engineer. Generate complete, buildable projects. Return JSON only."))
            _write_files(workspace, files)
            # The plan is embedded in resolved_goal. Validation remains independent of compiler success.
            artifact_type = ""
            try:
                marker = "SOFTWARE ENGINEERING PLAN:\n"
                if marker in resolved_goal:
                    plan_text = resolved_goal.split(marker, 1)[1].split("\n\nRESEARCH BUNDLE:", 1)[0]
                    plan_data = json.loads(plan_text)
                    artifact_type = str(plan_data.get("artifact_type") or "")
            except Exception:
                plan_data = {"artifact_type": artifact_type}
            plan_data = locals().get("plan_data") or {"artifact_type": artifact_type}
            semantic_defects = validate_generated_project(workspace, plan_data, language)
            if semantic_defects:
                last_error = "\n".join(semantic_defects)
                last_diagnosis = _diagnose_failure(llm, "semantic_validation", last_error)
                continue
            if requirements is None:
                try:
                    requirements = plan_data.get("tool_requirements") if isinstance(plan_data, dict) else None
                except Exception:
                    requirements = None
            install = (
                _run(language, "install", workspace, timeout, requirements)
                if _has_lifecycle_command(requirements, "install")
                else {"operation": "install", "passed": True, "skipped": True, "not_required": True}
            )
            if not install.get("passed"):
                last_error = install.get("error") or install.get("output") or "dependency installation failed"
                last_diagnosis = _diagnose_failure(llm, "install", last_error)
                continue
            build = _run(language, "build", workspace, timeout, requirements)
            if not build.get("passed"):
                last_error = build.get("error") or build.get("output") or "build failed"
                last_diagnosis = _diagnose_failure(llm, "build", last_error)
                continue
            tests = _run(language, "test", workspace, timeout, requirements)
            lint = _run(language, "lint", workspace, timeout, requirements)
            typecheck = _run(language, "typecheck", workspace, timeout, requirements) if _has_lifecycle_command(requirements, "typecheck") else {"operation": "typecheck", "passed": True, "skipped": True, "not_required": True}
            run = (
                _run(language, "run", workspace, timeout, requirements)
                if _has_lifecycle_command(requirements, "run")
                else {"operation": "run", "passed": False, "skipped": True, "blocked": True, "reason": "No runtime validation command was declared for this artifact."}
            )
            if tests.get("passed") and lint.get("passed") and typecheck.get("passed") and run.get("passed"):
                break
            last_error = tests.get("error") or tests.get("output") or lint.get("error") or lint.get("output") or typecheck.get("error") or typecheck.get("output") or run.get("error") or run.get("output") or "tests/lint/runtime validation failed"
            last_diagnosis = _diagnose_failure(llm, "tests_lint_runtime", last_error)
    status = "built" if build.get("passed") and tests.get("passed", False) and lint.get("passed", False) and typecheck.get("passed", False) and run.get("passed", False) and not semantic_defects else "build_failed"
    pid = execute("INSERT INTO generated_projects(language,request,code) VALUES(?,?,?)", (language, resolved_goal, json.dumps(files, ensure_ascii=False)))
    return {
        "status": status, "language": language, "request": resolved_goal, "project_id": pid, "project_name": workspace.name,
        "project_path": str(workspace.relative_to(ROOT)) if workspace.is_relative_to(ROOT) else str(workspace), "session_id": session_id,
        "files": sorted(files), "file_count": len(files), "install": install, "build": build, "tests": tests, "lint": lint, "typecheck": typecheck, "run": run, "phase_validation": phase_validation,
        "semantic_defects": semantic_defects, "repair_attempts": attempts - 1, "failure_diagnosis": last_diagnosis, "artifacts": _artifact_files(workspace),
        "toolchain": doctor(language, cwd=str(workspace), requirements=requirements),
    }


def project_status(project_path: str) -> dict[str, Any]:
    root = (ROOT / project_path).resolve() if not os.path.isabs(project_path) else Path(project_path).resolve()
    projects = (ROOT / "projects").resolve()
    root.relative_to(projects)
    files = [str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if p.is_file()]
    return {"project_path": str(root.relative_to(ROOT)), "files": sorted(files), "artifacts": _artifact_files(root)}
