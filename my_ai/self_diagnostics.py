from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from .db import execute, fetch_all
from .access_policy import assert_mutation_allowed

ROOT = Path(__file__).resolve().parent.parent
REPORT_ROOT = ROOT / "data" / "diagnostics"
DEFAULT_INTERVAL_SECONDS = 900


def _run(args: list[str], timeout: int = 120) -> tuple[int, str]:
    try:
        env = os.environ.copy()
        # Diagnostics invoke pytest as a subprocess. Disable the diagnostics
        # monitor inside that child so pytest cannot recursively launch pytest.
        if "-m" in args and "pytest" in args:
            env["MYAI_DISABLE_SELF_DIAGNOSTICS"] = "1"
        p = subprocess.run(
            args,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=env,
        )
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
    except Exception as exc:
        logging.getLogger(__name__).debug("CPU diagnostics unavailable: %s", exc)
    try:
        import psutil
        info["ram_bytes"] = psutil.virtual_memory().total
    except Exception as exc:
        logging.getLogger(__name__).debug("RAM diagnostics unavailable: %s", exc)
    return info


def run_diagnostics() -> dict[str, object]:
    assert_mutation_allowed("diagnostic report")
    checks: dict[str, dict[str, object]] = {}

    code, output = _run([sys.executable, "-m", "compileall", "-q", "my_ai"], 120)
    checks["compileall"] = {"ok": code == 0, "output": output[-12000:]}

    # Running the full test suite from the live server creates a large
    # temporary pytest tree and can spawn test processes that contend with
    # the application's SQLite database. Keep it opt-in for diagnostics.
    if os.environ.get("MYAI_SELF_DIAGNOSTICS_RUN_TESTS") == "1":
        code, output = _run([sys.executable, "-m", "pytest", "-q"], 300)
        checks["pytest"] = {"ok": code == 0, "output": output[-20000:]}
    else:
        checks["pytest"] = {
            "ok": True,
            "skipped": True,
            "reason": "full pytest run is opt-in to avoid production temp files and DB contention",
        }

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


def _report_fingerprint(report: dict[str, object]) -> str:
    stable = dict(report)
    stable.pop("timestamp", None)
    stable.pop("id", None)
    stable.pop("created_at", None)
    return json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def report_history(limit: int = 20) -> list[dict[str, object]]:
    rows = fetch_all(
        "SELECT id,created_at,healthy,report_json "
        "FROM self_diagnostic_reports ORDER BY id DESC LIMIT 1000"
    )
    result = []
    seen: set[str] = set()
    for row in rows:
        try:
            item = json.loads(row["report_json"])
        except Exception:
            item = {"raw": row["report_json"]}
        fingerprint = _report_fingerprint(item)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        item["id"] = row["id"]
        item["created_at"] = row["created_at"]
        result.append(item)
        if len(result) >= max(1, min(int(limit), 100)):
            break
    return result


def paginated_report_history(page: int = 1, page_size: int = 10) -> dict[str, object]:
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 10))
    rows = fetch_all(
        "SELECT id,created_at,healthy,report_json "
        "FROM self_diagnostic_reports ORDER BY id DESC LIMIT 1000"
    )
    result = []
    seen: set[str] = set()
    for row in rows:
        try:
            item = json.loads(row["report_json"])
        except Exception:
            item = {"raw": row["report_json"]}
        fingerprint = _report_fingerprint(item)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        item["id"] = row["id"]
        item["created_at"] = row["created_at"]
        result.append(item)
    total = len(result)
    start = (page - 1) * page_size
    return {
        "reports": result[start:start + page_size],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


class SelfDiagnosticsMonitor:
    def __init__(self, interval_seconds: int = DEFAULT_INTERVAL_SECONDS):
        self.interval_seconds = max(60, int(interval_seconds))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        # Never start the monitor from a pytest process. The monitor itself
        # runs pytest, so allowing it to start here would recurse indefinitely.
        under_pytest = (
            os.environ.get("MYAI_DISABLE_SELF_DIAGNOSTICS") == "1"
            or "PYTEST_CURRENT_TEST" in os.environ
            or any("pytest" in str(arg).lower() for arg in sys.argv)
        )
        if under_pytest:
            return
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
        except Exception as exc:
            logging.getLogger(__name__).debug("Diagnostic cycle failed: %s", exc)
        while not self._stop.wait(self.interval_seconds):
            try:
                run_diagnostics()
            except Exception:
                pass
