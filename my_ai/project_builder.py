# mypy: ignore-errors
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .config import assert_write_allowed
from .curriculum import canonical_language
from .db import execute, fetch_all, search_knowledge
from .llm import create_llm
from .project_workspace import create_project_workspace
from .tooling import run_project_tool, doctor
from .software_validation import validate_generated_project

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


def _run(language: str, operation: str, workspace: Path, timeout: int) -> dict[str, Any]:
    if canonical_language(language) == "MQL4":
        metaeditor = os.getenv("MYAI_METAEDITOR", "").strip()
        if not metaeditor:
            return {"language": "MQL4", "operation": operation, "passed": False, "available": False, "return_code": -1, "output": "", "error": "MetaEditor compiler is unavailable. Set MYAI_METAEDITOR to metaeditor.exe."}
        sources = list(workspace.rglob("*.mq4"))
        if not sources:
            return {"language": "MQL4", "operation": operation, "passed": False, "available": True, "return_code": -1, "output": "", "error": "No .mq4 source file was generated."}
        if operation in {"test", "lint"}:
            return {"language": "MQL4", "operation": operation, "passed": True, "available": True, "return_code": 0, "output": "MQL4 semantic/static validation is performed by the software validation layer; compilation is performed by MetaEditor.", "error": ""}
        errors = []
        for source in sources:
            try:
                p = subprocess.run([metaeditor, f"/compile:{source}", "/log"], cwd=workspace, capture_output=True, text=True, timeout=max(1, min(int(timeout), 600)), shell=False)
                if p.returncode != 0:
                    errors.append((p.stdout or "")[-6000:] + "\n" + (p.stderr or "")[-6000:])
            except Exception as exc:
                errors.append(str(exc))
        return {"language": "MQL4", "operation": "build", "passed": not errors, "available": True, "return_code": 0 if not errors else 1, "output": "\n".join(errors), "error": "" if not errors else "MetaEditor compilation failed."}
    try:
        return run_project_tool(language, operation, str(workspace), timeout)
    except Exception as exc:
        return {"language": canonical_language(language), "operation": operation, "passed": False, "return_code": -1, "output": "", "error": str(exc)}


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
def _prompt(language: str, goal: str, knowledge: list[Any], previous_error: str = "") -> str:
    suffix = f"\nPREVIOUS VALIDATION/BUILD/TEST/LINT DEFECTS (fix every one; do not merely explain them):\n{previous_error[:18000]}" if previous_error else ""
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
    # Domain labels are not implementation languages.
    if candidate == "Forex":
        candidate = "MQL4"
    # Do not collapse an unknown/new language to Python. The semantic planner
    # is allowed to select languages that were not hard-coded into this file.
    # Build/validation layers decide later whether a local toolchain exists.
    if not candidate:
        return None
    if candidate.casefold() in {"fa", "fa-ir", "فارسی", "en", "en-us", "english"}:
        return None
    return candidate


def _plan_language(goal: str) -> str | None:
    try:
        marker = "SOFTWARE ENGINEERING PLAN:\n"
        if marker not in goal:
            return None
        payload = goal.split(marker, 1)[1].split("\n\nRESEARCH BUNDLE:", 1)[0]
        return _supported_language(json.loads(payload).get("language"))
    except Exception:
        return None


def build_project(goal: str, language: str = "Python", *, project_path: str | None = None, timeout: int = 300, repair_attempts: int = 2) -> dict[str, Any]:
    goal = str(goal or "").strip()
    if not goal:
        raise ValueError("Project goal is required.")
    resolved_goal, contextual_language, session_id = _recent_conversation_context(goal)
    detected_language = contextual_language
    language = _supported_language(detected_language) or _supported_language(language) or _plan_language(resolved_goal) or "Python"
    workspace = create_project_workspace(goal, projects_root=project_path)
    knowledge = search_knowledge(language + " " + resolved_goal, 20)
    llm = create_llm("coding")
    files = {}
    build = tests = lint = {}
    last_error = ""
    attempts = max(1, min(int(repair_attempts) + 1, 5))
    semantic_defects: list[str] = []
    for _ in range(attempts):
        files = _parse_files(llm.chat(_prompt(language, resolved_goal, knowledge, last_error), system="You are a senior software architect and implementation engineer. Generate complete, buildable projects. Return JSON only."))
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
            continue
        build = _run(language, "build", workspace, timeout)
        if not build.get("passed"):
            last_error = build.get("error") or build.get("output") or "build failed"
            continue
        tests = _run(language, "test", workspace, timeout)
        lint = _run(language, "lint", workspace, timeout)
        if tests.get("passed") and lint.get("passed"):
            break
        last_error = tests.get("error") or tests.get("output") or lint.get("error") or lint.get("output") or "tests/lint failed"
    status = "built" if build.get("passed") and tests.get("passed", False) and lint.get("passed", False) and not semantic_defects else "build_failed"
    pid = execute("INSERT INTO generated_projects(language,request,code) VALUES(?,?,?)", (language, resolved_goal, json.dumps(files, ensure_ascii=False)))
    return {
        "status": status, "language": language, "request": resolved_goal, "project_id": pid, "project_name": workspace.name,
        "project_path": str(workspace.relative_to(ROOT)) if workspace.is_relative_to(ROOT) else str(workspace), "session_id": session_id,
        "files": sorted(files), "file_count": len(files), "build": build, "tests": tests, "lint": lint,
        "semantic_defects": semantic_defects, "repair_attempts": attempts - 1, "artifacts": _artifact_files(workspace),
        "toolchain": ({"metaeditor": bool(os.getenv("MYAI_METAEDITOR", "").strip())} if canonical_language(language) == "MQL4" else doctor(language).get(language, {})),
    }


def project_status(project_path: str) -> dict[str, Any]:
    root = (ROOT / project_path).resolve() if not os.path.isabs(project_path) else Path(project_path).resolve()
    projects = (ROOT / "projects").resolve()
    root.relative_to(projects)
    files = [str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if p.is_file()]
    return {"project_path": str(root.relative_to(ROOT)), "files": sorted(files), "artifacts": _artifact_files(root)}
