from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import settings


@dataclass(frozen=True)
class ExecutionResult:
    output: str
    error: str
    timed_out: bool
    return_code: int


def run_python(code: str) -> ExecutionResult:
    with tempfile.TemporaryDirectory(prefix="myai-") as tmp:
        script = Path(tmp) / "main.py"
        script.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, str(script)],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=settings.exec_timeout,
            )
            return ExecutionResult(
                output=proc.stdout[-12000:],
                error=proc.stderr[-12000:],
                timed_out=False,
                return_code=proc.returncode,
            )
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(
                output=(exc.stdout or "")[-12000:] if isinstance(exc.stdout, str) else "",
                error="Execution timed out.",
                timed_out=True,
                return_code=-1,
            )
