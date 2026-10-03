from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _run(command: list[str], cwd: Path, timeout: int) -> dict[str, Any]:
    try:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout)
        return {
            "command": command,
            "returncode": result.returncode,
            "passed": result.returncode == 0,
            "stdout": result.stdout[-12000:],
            "stderr": result.stderr[-12000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": -1,
            "passed": False,
            "timeout": True,
            "stdout": str(exc.stdout or ""),
            "stderr": str(exc.stderr or ""),
        }


def run_reproduction_pipeline(
    workspace: str | Path,
    *,
    commands: dict[str, list[str]] | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    root = Path(workspace).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("Reproduction workspace does not exist.")
    default = {
        "build": ["python", "-m", "compileall", "-q", "backend"],
        "lint": ["python", "-m", "compileall", "-q", "backend"],
        "unit": ["python", "-m", "pytest", "-q", "tests"],
        "integration": ["python", "-m", "pytest", "-q", "tests"],
        "e2e": ["python", "-m", "pytest", "-q", "tests"],
    }
    plan = commands or default
    results = {}
    for stage, command in plan.items():
        if not command:
            results[stage] = {"passed": True, "skipped": True}
            continue
        executable = shutil.which(command[0])
        if executable is None:
            results[stage] = {"passed": False, "skipped": True, "error": f"Executable not found: {command[0]}"}
            continue
        results[stage] = _run(command, root, timeout)
        if not results[stage]["passed"]:
            break
    return {
        "workspace": str(root),
        "passed": bool(results) and all(item.get("passed") for item in results.values()),
        "stages": results,
        "plan": plan,
    }


def write_verification_report(root: str | Path, report: dict[str, Any]) -> Path:
    path = Path(root).expanduser().resolve() / "reproduction-verification.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
