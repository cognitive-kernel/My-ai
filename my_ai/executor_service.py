from __future__ import annotations

import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="My-AI Executor", docs_url=None, redoc_url=None)
TOKEN = os.getenv("EXECUTOR_SHARED_TOKEN", "")
IMAGE = os.getenv("EXECUTOR_IMAGE", "python:3.11-slim")
TIMEOUT = int(os.getenv("EXEC_TIMEOUT", "10"))
MEMORY = os.getenv("EXEC_MEMORY", "256m")
CPUS = os.getenv("EXEC_CPUS", "1.0")
PIDS = int(os.getenv("EXEC_PIDS", "64"))
OUTPUT = int(os.getenv("EXEC_OUTPUT_CHARS", "12000"))


class RunRequest(BaseModel):
    code: str


def trunc(value: str) -> str:
    return (value or "")[-OUTPUT:]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run")
def run(req: RunRequest, authorization: str | None = Header(default=None)):
    if not TOKEN or authorization != f"Bearer {TOKEN}":
        raise HTTPException(401, "Unauthorized")
    if not req.code.strip() or len(req.code) > 200_000:
        raise HTTPException(400, "Invalid code payload.")
    name = f"myai-exec-{uuid.uuid4().hex[:16]}"
    with tempfile.TemporaryDirectory(prefix="myai-exec-") as tmp:
        path = Path(tmp) / "main.py"
        path.write_text(req.code, encoding="utf-8")
        os.chmod(path, 0o644)
        cmd = [
            "docker","run","--rm","--name",name,"--network","none","--read-only",
            "--cap-drop","ALL","--security-opt","no-new-privileges",
            "--pids-limit",str(PIDS),"--memory",MEMORY,"--cpus",CPUS,
            "--user","65532:65532","--tmpfs","/tmp:rw,noexec,nosuid,size=64m",
            "--mount",f"type=bind,src={tmp},dst=/work,readonly",
            IMAGE,"python","-I","/work/main.py",
        ]
        try:
            result=subprocess.run(cmd,capture_output=True,text=True,timeout=TIMEOUT+2)
            return {"output":trunc(result.stdout),"error":trunc(result.stderr),
                    "timed_out":False,"return_code":result.returncode}
        except subprocess.TimeoutExpired:
            subprocess.run(["docker","rm","-f",name],capture_output=True,timeout=5)
            return {"output":"","error":"Execution timed out; container was terminated.",
                    "timed_out":True,"return_code":-1}
