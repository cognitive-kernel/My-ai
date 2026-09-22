from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from .db import execute

ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "data" / "self_update"
STATE_DIR.mkdir(parents=True, exist_ok=True)
LESSONS = STATE_DIR / "lessons.jsonl"


def _run(args, cwd=ROOT, timeout=120):
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)


def _stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _git(*args, timeout=120):
    r = _run(["git", *args], timeout=timeout)
    if r.returncode:
        raise RuntimeError((r.stderr or r.stdout or "git command failed").strip())
    return r.stdout.strip()


def _record_lesson(event, **data):
    item = {"time": datetime.now(timezone.utc).isoformat(), "event": event, **data}
    with LESSONS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    try:
        execute("INSERT INTO fix_attempts(event,patch,test_result,activated) VALUES(?,?,?,?)",
                (event, data.get("candidate") or data.get("attempted"), data.get("details") or data.get("error"), 1 if event == "update_activated" else 0))
    except Exception:
        pass


def _tests(cwd):
    compile_run = _run([sys.executable, "-m", "compileall", "-q", "my_ai"], cwd=cwd, timeout=120)
    if compile_run.returncode:
        return False, "compileall failed:\n" + (compile_run.stdout + compile_run.stderr).strip()
    tests_dir = cwd / "tests"
    if tests_dir.exists():
        test_run = _run([sys.executable, "-m", "pytest", "-q"], cwd=cwd, timeout=300)
        if test_run.returncode:
            return False, "pytest failed:\n" + (test_run.stdout + test_run.stderr).strip()
        return True, "compileall + pytest passed"
    return True, "compileall passed; no tests directory present"


def status():
    try:
        branch = _git("branch", "--show-current")
        head = _git("rev-parse", "HEAD")
        dirty = bool(_git("status", "--porcelain"))
        return {"ok": True, "branch": branch, "head": head, "dirty": dirty}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def check_for_update():
    try:
        if _git("status", "--porcelain"):
            return {"ok": False, "update_available": False, "blocked": True, "reason": "working tree is not clean"}
        _git("fetch", "origin", "main", timeout=120)
        local = _git("rev-parse", "HEAD")
        remote = _git("rev-parse", "origin/main")
        return {"ok": True, "update_available": local != remote, "local": local, "remote": remote}
    except Exception as exc:
        return {"ok": False, "update_available": False, "error": str(exc)}


def apply_confirmed_update(health_url=None, health_timeout=45):
    """Test origin/main in isolation, snapshot current code, fast-forward, then supervise restart."""
    if _git("status", "--porcelain"):
        raise RuntimeError("Self-update متوقف شد: ابتدا تغییرات محلی را commit کنید یا در جای امن نگه دارید.")
    if os.getenv("MYAI_SELF_UPDATE_ENABLED", "false").strip().lower() != "true":
        raise RuntimeError("Self-update is deny-by-default. Set MYAI_SELF_UPDATE_ENABLED=true only after explicit user approval and policy review.")
    if os.getenv("MYAI_SELF_UPDATE_APPROVED", "false").strip().lower() != "true":
        raise RuntimeError("Self-update requires an explicit approval gate.")

    _git("fetch", "origin", "main", timeout=120)
    current = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "origin/main")
    if current == remote:
        return {"status": "up_to_date", "commit": current}

    stamp = _stamp()
    backup = f"myai-preupdate-{stamp}"
    candidate = STATE_DIR / f"candidate-{stamp}"
    _git("tag", "-a", backup, "-m", "My-AI automatic pre-update snapshot")

    try:
        _git("worktree", "add", "--detach", str(candidate), "origin/main", timeout=120)
        ok, details = _tests(candidate)
        if not ok:
            _record_lesson("candidate_test_failed", base=current, candidate=remote, details=details)
            return {"status": "blocked", "reason": "candidate tests failed", "details": details, "backup": backup}

        _git("worktree", "remove", "--force", str(candidate), timeout=120)
        candidate = None
        _git("merge", "--ff-only", "origin/main", timeout=120)
        _record_lesson("update_activated", previous=current, new=remote, backup=backup)

        command = os.getenv("MYAI_RESTART_COMMAND", "").strip()
        if not command:
            command = f'"{sys.executable}" -m uvicorn my_ai.api:app --host 127.0.0.1 --port 8000'
        cmd = shlex.split(command, posix=(os.name != "nt"))
        watchdog = [
            sys.executable,
            "-m",
            "my_ai.watchdog",
            "--pid",
            str(os.getpid()),
            "--rollback",
            backup,
            "--timeout",
            str(health_timeout),
            "--command",
            command,
        ]
        if health_url:
            watchdog += ["--url", health_url]
        subprocess.Popen(
            watchdog,
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        return {"status": "activated", "previous": current, "current": remote, "backup": backup, "watchdog": True, "restart_command": cmd}
    except Exception as exc:
        _record_lesson("update_failed", previous=current, attempted=remote, backup=backup, error=str(exc))
        raise
    finally:
        if candidate and candidate.exists():
            try:
                _git("worktree", "remove", "--force", str(candidate), timeout=120)
            except Exception:
                pass


def recent_lessons(limit=20):
    if not LESSONS.exists():
        return []
    lines = LESSONS.read_text(encoding="utf-8").splitlines()[-max(1, min(limit, 100)):]
    result = []
    for line in lines:
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return result
