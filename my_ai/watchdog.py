from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import time
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
LESSONS = ROOT / "data" / "self_update" / "lessons.jsonl"

def _record_lesson(event, **data):
    LESSONS.parent.mkdir(parents=True, exist_ok=True)
    item={"time":datetime.now(timezone.utc).isoformat(),"event":event,**data}
    with LESSONS.open("a",encoding="utf-8") as f:
        f.write(json.dumps(item,ensure_ascii=False)+"\n")


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, timeout=60)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pid", type=int, required=True)
    p.add_argument("--rollback", required=True)
    p.add_argument("--timeout", type=int, default=45)
    p.add_argument("--url", default="http://127.0.0.1:8000/health")
    p.add_argument("--command", required=True)
    args = p.parse_args()

    # Give the parent a moment to exit/restart after the update.
    deadline = time.time() + max(10, args.timeout)
    while time.time() < deadline:
        if not _pid_alive(args.pid):
            break
        time.sleep(0.5)

    # If the old process is still alive, terminate it so the new revision can start.
    if _pid_alive(args.pid):
        _terminate(args.pid)
        time.sleep(1)

    command = shlex.split(args.command, posix=(os.name != "nt"))
    child = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)

    healthy = False
    deadline = time.time() + max(10, args.timeout)
    while time.time() < deadline:
        try:
            r = httpx.get(args.url, timeout=3)
            if r.status_code == 200:
                healthy = True
                break
        except Exception:
            pass
        if child.poll() is not None:
            break
        time.sleep(1)

    if healthy:
        return 0

    try:
        child.terminate()
        child.wait(timeout=5)
    except Exception:
        try:
            child.kill()
        except Exception:
            pass

    failed_tag = f"myai-failed-activation-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}"
    _git("tag", "-a", failed_tag, "-m", "My-AI failed activation snapshot")
    rollback = _git("reset", "--hard", args.rollback)
    if rollback.returncode:
        _record_lesson("activation_rollback_failed", rollback=args.rollback, error=rollback.stderr or rollback.stdout)
        return 2
    _record_lesson("activation_failed", rollback=args.rollback, failed_tag=failed_tag, health_url=args.url)

    subprocess.Popen(command, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, start_new_session=True)
    return 1


def _pid_alive(pid):
    if pid <= 0:
        return False
    if os.name == "nt":
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
        return str(pid) in r.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _terminate(pid):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.kill(pid, 15)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
