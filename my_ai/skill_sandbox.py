from __future__ import annotations

import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .skill_engine import record_evidence

def run(skill_id: int, command: list[str], *, cwd: str | None = None, timeout: int = 30) -> dict[str, Any]:
    if not command or any(not str(x).strip() for x in command):
        raise ValueError("Sandbox command is required.")
    timeout = max(1, min(300, int(timeout)))
    with tempfile.TemporaryDirectory(prefix="myai-skill-") as tmp:
        root = Path(cwd).resolve() if cwd else Path(tmp)
        root.mkdir(parents=True, exist_ok=True)
        result = subprocess.run([str(x) for x in command], cwd=root, text=True, capture_output=True, timeout=timeout)
        artifact = hashlib.sha256((result.stdout + "\n" + result.stderr).encode("utf-8","replace")).hexdigest()
        details={"command":" ".join(command),"artifact":artifact,"stdout":result.stdout[-4000:],"stderr":result.stderr[-4000:],"sandbox":True}
        evidence_id=record_evidence(skill_id,"test",result.returncode==0,details)
        return {"passed":result.returncode==0,"returncode":result.returncode,"evidence_id":evidence_id,"artifact":artifact,"stdout":result.stdout[-4000:],"stderr":result.stderr[-4000:]}
