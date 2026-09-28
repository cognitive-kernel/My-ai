# mypy: ignore-errors
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from .command_policy import LANGUAGE_ALIASES, _detect_language
from .config import assert_write_allowed
from .curriculum import canonical_language
from .db import execute, fetch_all, search_knowledge
from .llm import create_llm
from .project_workspace import create_project_workspace
from .tooling import run_project_tool, doctor

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


def _parse_files(raw: str) -> dict[str, str]:
    data = json.loads(_strip_fence(raw))
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
            return {"language": "MQL4", "operation": operation, "passed": False, "return_code": -1,
                    "output": "", "error": "MetaEditor compiler is unavailable. Set MYAI_METAEDITOR to metaeditor.exe."}
        if operation != "build":
            return {"language": "MQL4", "operation": operation, "passed": True, "return_code": 0,
                    "output": "No standard MQL4 test/lint command configured.", "error": ""}
        sources = list(workspace.rglob("*.mq4"))
        if not sources:
            return {"language": "MQL4", "operation": "build", "passed": False, "return_code": -1,
                    "output": "", "error": "No .mq4 source file was generated."}
        errors = []
        for source in sources:
            try:
                p = subprocess.run(
                    [metaeditor, f"/compile:{source}", "/log"], cwd=workspace,
                    capture_output=True, text=True, timeout=max(1, min(int(timeout), 600)), shell=False,
                )
                if p.returncode != 0:
                    errors.append((p.stdout or "")[-6000:] + "\n" + (p.stderr or "")[-6000:])
            except Exception as exc:
                errors.append(str(exc))
        return {"language": "MQL4", "operation": "build", "passed": not errors,
                "return_code": 0 if not errors else 1, "output": "\n".join(errors),
                "error": "" if not errors else "MetaEditor compilation failed."}
    try:
        return run_project_tool(language, operation, str(workspace), timeout)
    except Exception as exc:
        return {"language": canonical_language(language), "operation": operation,
                "passed": False, "return_code": -1, "output": "", "error": str(exc)}


def _is_contextual_build_request(goal: str) -> bool:
    text = re.sub(r"\s+", " ", str(goal or "").strip().casefold())
    markers = (
        "فایل رو بساز", "فایل را بساز", "فایل بساز", "همونو بساز", "همان را بساز",
        "همون فایل رو بساز", "بر اساس دستوراتی که دادم", "طبق دستوراتی که دادم",
        "بر اساس چیزی که گفتم", "همین رو بساز", "همین را بساز", "create it", "build it",
        "make it", "generate it",
    )
    return any(marker in text for marker in markers)


def _detect_language_from_texts(texts: list[str]) -> str | None:
    for text in reversed(texts):
        normalized = str(text or "").casefold()
        for alias, canonical in sorted(LANGUAGE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
            if alias.casefold() in normalized:
                try:
                    return canonical_language(canonical)
                except Exception:
                    return canonical
    return None


def _recent_conversation_context(goal: str) -> tuple[str, str | None, int | None]:
    sessions = fetch_all(
        "SELECT id,language FROM chat_sessions WHERE kind='chat' ORDER BY updated_at DESC,id DESC LIMIT 1"
    )
    if not sessions:
        return goal, None, None
    session_id = int(sessions[0]["id"])
    rows = fetch_all(
        "SELECT role,content FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT 80",
        (session_id,),
    )[::-1]
    user_messages = [str(row["content"] or "").strip() for row in rows if row["role"] == "user"]
    if not user_messages:
        return goal, sessions[0].get("language"), session_id

    current = str(goal or "").strip()
    current_language = _detect_language_from_texts([current])
    prior = None
    if _is_contextual_build_request(current):
        for candidate in reversed(user_messages[:-1]):
            if len(candidate) < 8:
                continue
            if _is_contextual_build_request(candidate):
                continue
            prior = candidate
            break
        if prior:
            resolved_goal = (
                "Previous user requirements from this same chat:\n"
                + prior
                + "\n\nCurrent user follow-up:\n"
                + current
            )
        else:
            resolved_goal = current
    else:
        resolved_goal = current

    prior_language = _detect_language_from_texts([prior]) if prior else _detect_language_from_texts(user_messages[:-1])
    resolved_language = _detect_language(resolved_goal.casefold())
    if not resolved_language:
        normalized_goal = resolved_goal.casefold()
        explicit_language_hints = (
            ("mql4", "MQL4"), ("mql 4", "MQL4"), ("mq4", "MQL4"),
            ("mql5", "MQL5"), ("python", "Python"), ("پایتون", "Python"),
            ("rust", "Rust"), ("javascript", "JavaScript"), ("typescript", "TypeScript"),
        )
        resolved_language = next((name for needle, name in explicit_language_hints if needle in normalized_goal), None)
    language = current_language or resolved_language or prior_language or sessions[0].get("language")
    if not language and _is_contextual_build_request(current):
        context_text = "\n".join(user_messages).casefold()
        if "mql4" in context_text or "mq4" in context_text or "متاتریدر 4" in context_text or "metatrader 4" in context_text:
            language = "MQL4"
    conversation_context = "\n".join(
        f"{row['role']}: {str(row['content'] or '')[:7000]}" for row in rows[-20:]
    )[:MAX_CONTEXT_CHARS]
    return resolved_goal + "\n\nFULL CHAT CONTEXT FOR THIS PROJECT REQUEST:\n" + conversation_context, language, session_id


def _prompt(language: str, goal: str, knowledge: list[Any], previous_error: str = "") -> str:
    suffix = f"\nPREVIOUS BUILD/TEST/LINT ERROR (fix it):\n{previous_error[:12000]}" if previous_error else ""
    return (
        "Generate a complete runnable software project, not a single source file. "
        "Return ONLY valid JSON: {\"files\":{\"relative/path\":\"file contents\"}}. "
        "The conversation context is authoritative for follow-up requests: if the current message says to build/create it, "
        "continue the user's previous concrete requirements instead of inventing a new task or language. "
        "Ignore previous assistant answers when they conflict with the user's own requirements. "
        "Create all necessary source files, dependency manifests, configuration, tests, and README build/run instructions. "
        "Use the requested language/framework and keep every path relative to the project root. "
        "Do not use absolute paths, secrets, runtime network downloads, or placeholder TODO implementations. "
        f"LANGUAGE: {language}\nGOAL: {goal}\n"
        f"LEARNED KNOWLEDGE: {json.dumps(knowledge, ensure_ascii=False)[:30000]}{suffix}"
    )


def _artifact_files(workspace: Path) -> list[str]:
    roots = ("dist", "build", "target", "bin", "out", "app/build/outputs")
    out = []
    for rel in roots:
        base = workspace / rel
        if base.exists():
            out.extend(str(p.relative_to(workspace)).replace("\\", "/") for p in base.rglob("*") if p.is_file())
    return out[:200]


def build_project(
    goal: str,
    language: str = "Python",
    *,
    project_path: str | None = None,
    timeout: int = 300,
    repair_attempts: int = 2,
) -> dict[str, Any]:
    goal = str(goal or "").strip()
    if not goal:
        raise ValueError("Project goal is required.")
    resolved_goal, contextual_language, session_id = _recent_conversation_context(goal)
    detected_language = contextual_language or _detect_language_from_texts([resolved_goal, goal])
    language = canonical_language(detected_language or language)
    workspace = create_project_workspace(goal, projects_root=project_path)
    knowledge = search_knowledge(language + " " + resolved_goal, 20)
    llm = create_llm("coding")
    files = {}
    build = tests = lint = {}
    last_error = ""
    attempts = max(1, min(int(repair_attempts) + 1, 4))
    for _ in range(attempts):
        files = _parse_files(llm.chat(
            _prompt(language, resolved_goal, knowledge, last_error),
            system="You are a senior software architect. Generate complete, buildable projects. Return JSON only.",
        ))
        _write_files(workspace, files)
        build = _run(language, "build", workspace, timeout)
        if not build.get("passed"):
            last_error = build.get("error") or build.get("output") or "build failed"
            continue
        tests = _run(language, "test", workspace, timeout) if language != "MQL4" else {
            "operation": "test", "passed": True,
            "note": "MQL4 test execution is delegated to MetaEditor/toolchain when available.",
        }
        lint = _run(language, "lint", workspace, timeout) if language != "MQL4" else {
            "operation": "lint", "passed": True, "note": "No standard MQL4 lint command configured.",
        }
        if tests.get("passed") and lint.get("passed"):
            break
        last_error = tests.get("error") or tests.get("output") or lint.get("error") or lint.get("output") or "tests/lint failed"
    pid = execute(
        "INSERT INTO generated_projects(language,request,code) VALUES(?,?,?)",
        (language, resolved_goal, json.dumps(files, ensure_ascii=False)),
    )
    return {
        "status": "built" if build.get("passed") and tests.get("passed", False) and lint.get("passed", False) else "build_failed",
        "language": language, "request": resolved_goal, "project_id": pid,
        "project_name": workspace.name,
        "project_path": str(workspace.relative_to(ROOT)) if workspace.is_relative_to(ROOT) else str(workspace),
        "session_id": session_id, "files": sorted(files), "file_count": len(files),
        "build": build, "tests": tests, "lint": lint, "repair_attempts": attempts - 1,
        "artifacts": _artifact_files(workspace),
        "toolchain": (
            {"metaeditor": bool(os.getenv("MYAI_METAEDITOR", "").strip())}
            if canonical_language(language) == "MQL4"
            else doctor(language).get(language, {})
        ),
    }


def project_status(project_path: str) -> dict[str, Any]:
    root = (ROOT / project_path).resolve() if not os.path.isabs(project_path) else Path(project_path).resolve()
    projects = (ROOT / "projects").resolve()
    root.relative_to(projects)
    files = [str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*") if p.is_file()]
    return {"project_path": str(root.relative_to(ROOT)), "files": sorted(files), "artifacts": _artifact_files(root)}
