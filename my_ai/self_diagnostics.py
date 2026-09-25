from __future__ import annotations

import json
import platform
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from .db import execute, fetch_all

ROOT = Path(__file__).resolve().parent.parent
REPORT_ROOT = ROOT / "data" / "diagnostics"
DEFAULT_INTERVAL_SECONDS = 900


def _run(args: list[str], timeout: int = 120) -> tuple[int, str]:
    try:
        p = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except Exception as exc:
        return 1, str(exc)


def _hardware() -> dict[str, object]:
    info: dict[str, object] = {
        "os": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "cpu_count": None,
        "ram_bytes": None,
    }
    try:
        import os
        info["cpu_count"] = os.cpu_count()
    except Exception:
        pass
    try:
        import psutil
        info["ram_bytes"] = psutil.virtual_memory().total
    except Exception:
        pass
    return info


def run_diagnostics() -> dict[str, object]:
    checks: dict[str, object] = {}

    code, output = _run([sys.executable, "-m", "compileall", "-q", "my_ai"], 120)
    checks["compileall"] = {"ok": code == 0, "output": output[-12000:]}

    code, output = _run([sys.executable, "-m", "pytest", "-q"], 300)
    checks["pytest"] = {"ok": code == 0, "output": output[-20000:]}

    code, output = _run(["git", "status", "--short"], 60)
    checks["git_status"] = {"ok": code == 0, "output": output[-12000:]}

    code, output = _run(["git", "rev-parse", "HEAD"], 60)
    checks["git_head"] = {"ok": code == 0, "output": output[-1000:]}

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": "initial-beta-report-only",
        "hardware": _hardware(),
        "checks": checks,
        "healthy": all(bool(v.get("ok")) for v in checks.values()),
        "automatic_changes": False,
        "recommendation": (
            "Report only during initial/beta phase. "
            "Do not modify source, dependencies, configuration or repository automatically."
        ),
    }

    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (REPORT_ROOT / f"{stamp}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    execute(
        """CREATE TABLE IF NOT EXISTS self_diagnostic_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            healthy INTEGER NOT NULL,
            report_json TEXT NOT NULL
        )"""
    )
    execute(
        "INSERT INTO self_diagnostic_reports(healthy,report_json) VALUES(?,?)",
        (1 if report["healthy"] else 0, json.dumps(report, ensure_ascii=False)),
    )
    return report


def latest_report() -> dict[str, object] | None:
    rows = fetch_all(
        "SELECT report_json FROM self_diagnostic_reports ORDER BY id DESC LIMIT 1"
    )
    if not rows:
        return None
    try:
        return json.loads(rows[0]["report_json"])
    except Exception:
        return None


def report_history(limit: int = 20) -> list[dict[str, object]]:
    rows = fetch_all(
        "SELECT id,created_at,healthy,report_json "
        "FROM self_diagnostic_reports ORDER BY id DESC LIMIT ?",
        (max(1, min(int(limit), 100)),),
    )
    result = []
    for row in rows:
        try:
            item = json.loads(row["report_json"])
        except Exception:
            item = {"raw": row["report_json"]}
        item["id"] = row["id"]
        item["created_at"] = row["created_at"]
        result.append(item)
    return result


class SelfDiagnosticsMonitor:
    def __init__(self, interval_seconds: int = DEFAULT_INTERVAL_SECONDS):
        self.interval_seconds = max(60, int(interval_seconds))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="myai-self-diagnostics",
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        try:
            run_diagnostics()
        except Exception:
            pass
        while not self._stop.wait(self.interval_seconds):
            try:
                run_diagnostics()
            except Exception:
                pass
