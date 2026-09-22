from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .db import execute
from .llm import create_llm
from .self_update import recent_lessons
from .decision_log import record as record_decision
from .notifications import notify

ROOT = Path(__file__).resolve().parent.parent
PROPOSALS = ROOT / "self-repair" / "proposals"


def _run(args, cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)


def _git(*args: str, cwd: Path = ROOT, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd, timeout)


def _tests(cwd: Path) -> tuple[bool, str]:
    compile_run = _run([sys.executable, "-m", "compileall", "-q", "my_ai"], cwd, 120)
    if compile_run.returncode:
        return False, "compileall failed:\n" + (compile_run.stdout + compile_run.stderr).strip()
    test_run = _run([sys.executable, "-m", "pytest", "-q"], cwd, 300)
    if test_run.returncode:
        return False, "pytest failed:\n" + (test_run.stdout + test_run.stderr).strip()
    return True, "compileall + pytest passed"


def _clean_git() -> bool:
    return not bool(_git("status", "--porcelain").stdout.strip())


def diagnose_local() -> dict[str, object]:
    head = _git("rev-parse", "HEAD")
    status = _git("status", "--short")
    tests_ok, tests = _tests(ROOT)
    lessons = recent_lessons(20)
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "head": head.stdout.strip(),
        "clean": not bool(status.stdout.strip()),
        "status": status.stdout,
        "tests_passed": tests_ok,
        "tests": tests,
        "lessons": lessons,
    }
    execute(
        "INSERT INTO fix_attempts(event,patch,test_result,activated) VALUES(?,?,?,?)",
        ("repair_diagnosis", None, tests, 0),
    )
    return result


def _normalize_patch(raw: str) -> str:
    patch = raw.strip()
    fence = chr(96) * 3
    if patch.startswith(fence):
        patch = patch[len(fence):].lstrip()
        if patch.startswith("diff"):
            pass
        elif "\n" in patch:
            patch = patch.split("\n", 1)[1].lstrip()
        if patch.endswith(fence):
            patch = patch[:-len(fence)].rstrip()
    if "diff --git " not in patch:
        raise ValueError("The model did not return a unified git patch.")
    return patch + "\n"


def _test_patch(patch: str, base: str) -> tuple[bool, str]:
    parent = Path(tempfile.mkdtemp(prefix="myai-repair-"))
    candidate = parent / "worktree"
    try:
        add = _git("worktree", "add", "--detach", str(candidate), base, timeout=120)
        if add.returncode:
            return False, "worktree creation failed:\n" + (add.stdout + add.stderr).strip()
        patch_file = candidate / ".myai-repair.patch"
        patch_file.write_text(patch, encoding="utf-8")
        check = _git("apply", "--check", str(patch_file), cwd=candidate)
        if check.returncode:
            return False, "git apply --check failed:\n" + (check.stdout + check.stderr).strip()
        apply = _git("apply", "--index", str(patch_file), cwd=candidate)
        if apply.returncode:
            return False, "git apply failed:\n" + (apply.stdout + apply.stderr).strip()
        return _tests(candidate)
    finally:
        _git("worktree", "remove", "--force", str(candidate), timeout=120)
        shutil.rmtree(parent, ignore_errors=True)


def propose_repair(issue: str) -> dict[str, object]:
    if not issue.strip():
        raise ValueError("A concrete local bug description is required.")
    diagnosis = diagnose_local()
    base = str(diagnosis["head"])
    prompt = (
        "You are the My-AI senior repair engineer. Diagnose the supplied local failure and propose the smallest safe source patch. "
        "Use the diagnosis and previous repair lessons as engineering evidence. Do not invent files or APIs. "
        "Return ONLY a valid unified git diff beginning with 'diff --git'. "
        "The patch must be applicable from the repository root and must include tests for the fix when practical.\n\n"
        f"ISSUE:\n{issue}\n\nDIAGNOSIS:\n{json.dumps(diagnosis, ensure_ascii=False, indent=2)}\n\n"
        f"RECENT LESSONS:\n{json.dumps(recent_lessons(20), ensure_ascii=False, indent=2)}"
    )
    llm = create_llm("coding")
    raw = ""
    patch = ""
    passed = False
    test_result = ""
    last_error = ""
    for attempt in range(3):
        retry_prompt = prompt
        if last_error:
            retry_prompt += "\n\nPREVIOUS OUTPUT WAS INVALID. REPAIR IT AND RETURN ONLY THE FULL VALID UNIFIED DIFF:\n" + last_error
        raw = llm.chat(retry_prompt, system="You generate minimal, testable git patches. Never return prose.")
        try:
            patch = _normalize_patch(raw)
        except ValueError as exc:
            last_error = str(exc) + "\nOUTPUT:\n" + raw[:12000]
            continue
        passed, test_result = _test_patch(patch, base)
        break
    if not patch:
        raise ValueError("The model failed to produce a valid unified git patch after 3 attempts.")
    proposal_id = uuid.uuid4().hex
    PROPOSALS.mkdir(parents=True, exist_ok=True)
    proposal = {
        "id": proposal_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base": base,
        "issue": issue,
        "patch": patch,
        "isolated_tests_passed": passed,
        "test_result": test_result,
        "approved": False,
        "applied": False,
    }
    (PROPOSALS / f"{proposal_id}.json").write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
    execute(
        "INSERT INTO fix_attempts(event,patch,test_result,activated) VALUES(?,?,?,?)",
        ("repair_proposal", patch, test_result, 0),
    )
    record_decision("self_repair_proposal", "propose", {"proposal_id": proposal_id, "isolated_tests_passed": passed})

    return proposal


def apply_repair(proposal_id: str, approved: bool) -> dict[str, object]:
    if not approved:
        raise ValueError("Explicit approval is required before applying a repair.")
    path = PROPOSALS / f"{proposal_id}.json"
    if not path.is_file():
        raise ValueError("Repair proposal not found.")
    proposal = json.loads(path.read_text(encoding="utf-8"))
    if not proposal.get("isolated_tests_passed"):
        raise ValueError("Only a repair proposal that passed isolated tests can be applied.")
    current = _git("rev-parse", "HEAD").stdout.strip()
    if current != proposal["base"]:
        raise ValueError("Repository HEAD changed since the proposal was generated; regenerate the repair.")
    if not _clean_git():
        raise ValueError("Working tree must be clean before applying a repair.")
    patch_file = PROPOSALS / f"{proposal_id}.patch"
    patch_file.write_text(str(proposal["patch"]), encoding="utf-8")
    applied = _git("apply", str(patch_file))
    if applied.returncode:
        execute("INSERT INTO fix_attempts(event,patch,test_result,activated) VALUES(?,?,?,?)",
                ("repair_apply_failed", proposal["patch"], applied.stderr or applied.stdout, 0))
        raise RuntimeError("Repair patch could not be applied:\n" + (applied.stderr or applied.stdout))
    ok, tests = _tests(ROOT)
    if not ok:
        _git("reset", "--hard", proposal["base"])
        execute("INSERT INTO fix_attempts(event,patch,test_result,activated) VALUES(?,?,?,?)",
                ("repair_rolled_back", proposal["patch"], tests, 0))
        raise RuntimeError("Applied repair failed post-apply tests and was rolled back:\n" + tests)
    proposal["approved"] = True
    proposal["applied"] = True
    proposal["applied_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding="utf-8")
    execute("INSERT INTO fix_attempts(event,patch,test_result,activated) VALUES(?,?,?,?)",
            ("repair_applied", proposal["patch"], tests, 1))
    record_decision("self_repair", "apply", {"proposal_id": proposal_id})
    notify("self_repair_applied", {"proposal_id": proposal_id, "base": proposal["base"]})
    return {
        "status": "applied",
        "proposal_id": proposal_id,
        "base": proposal["base"],
        "tests": tests,
        "working_tree": "modified",
    }

def list_proposals() -> list[dict[str, object]]:
    PROPOSALS.mkdir(parents=True, exist_ok=True)
    items = []
    for path in sorted(PROPOSALS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
            items.append({k: item.get(k) for k in ("id","created_at","base","issue","isolated_tests_passed","approved","applied")})
        except Exception:
            continue
    return items[:100]

def proposal_diff(proposal_id: str) -> dict[str, object]:
    proposal = proposal_status(proposal_id)
    return {"id": proposal_id, "base": proposal.get("base"), "issue": proposal.get("issue"), "diff": proposal.get("patch", "")}


def proposal_status(proposal_id: str) -> dict[str, object]:
    path = PROPOSALS / f"{proposal_id}.json"
    if not path.is_file():
        raise ValueError("Repair proposal not found.")
    return json.loads(path.read_text(encoding="utf-8"))
