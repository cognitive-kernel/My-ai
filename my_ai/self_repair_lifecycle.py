from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from .db import execute
from .state_backup import database_snapshot, restore_database_snapshot

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / 'self-repair'

def activate_with_safety(proposal_id: str, base_ref: str, apply_patch, run_tests, health_url: str | None = None, health_timeout: float = 20.0) -> dict:
    STATE.mkdir(parents=True, exist_ok=True)
    snapshot = database_snapshot(STATE / f'{proposal_id}.pre.sqlite')
    result = {'proposal_id': proposal_id, 'base': base_ref, 'snapshot': snapshot, 'activated': False}
    try:
        apply_patch()
        ok, tests = run_tests()
        result['tests'] = tests
        if not ok:
            raise RuntimeError('candidate tests failed')
        if health_url:
            deadline = time.monotonic() + max(1.0, float(health_timeout))
            healthy = False
            last_error = ''
            while time.monotonic() < deadline:
                try:
                    with urllib.request.urlopen(health_url, timeout=3) as response:
                        healthy = int(response.status) == 200
                        if healthy: break
                except Exception as exc:
                    last_error = str(exc)
                time.sleep(0.5)
            if not healthy:
                raise RuntimeError(f'health check failed: {last_error}')
        result['activated'] = True
        result['health_checked'] = bool(health_url)
        execute('INSERT INTO fix_attempts(event,patch,test_result,activated) VALUES(?,?,?,?)', ('repair_activation', proposal_id, json.dumps(result, ensure_ascii=False), 1))
        return result
    except Exception as exc:
        result['error'] = str(exc)
        try:
            restore_database_snapshot(Path(snapshot))
            result['database_restored'] = True
        except Exception as restore_error:
            result['database_restored'] = False
            result['restore_error'] = str(restore_error)
        result['activated'] = False
        try:
            import subprocess
            rollback = subprocess.run(["git", "reset", "--hard", base_ref], cwd=ROOT, text=True, capture_output=True, timeout=120)
            result["git_rolled_back"] = rollback.returncode == 0
            if rollback.returncode != 0:
                result["git_rollback_error"] = (rollback.stderr or rollback.stdout).strip()
        except Exception as rollback_error:
            result["git_rolled_back"] = False
            result["git_rollback_error"] = str(rollback_error)
        lesson = STATE / 'lessons.jsonl'
        with lesson.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'event':'activation_failed', **result}, ensure_ascii=False) + '\n')
        execute('INSERT INTO fix_attempts(event,patch,test_result,activated) VALUES(?,?,?,?)', ('repair_activation_failed', proposal_id, str(exc), 0))
        raise

def snapshot_for_proposal(proposal_id: str) -> str:
    return database_snapshot(STATE / f'{proposal_id}.pre.sqlite')