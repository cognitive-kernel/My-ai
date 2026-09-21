from __future__ import annotations

import hmac
import os
import subprocess
import uuid

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
    expected=f"Bearer {TOKEN}"
    if not TOKEN or TOKEN == "replace-with-a-long-random-secret" or not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(401, "Unauthorized")
    if not req.code.strip() or len(req.code) > 200_000:
        raise HTTPException(400, "Invalid code payload.")
    name = f"myai-exec-{uuid.uuid4().hex[:16]}"
    cmd = [
        "docker","run","--rm","-i","--name",name,"--network","none","--read-only",
        "--cap-drop","ALL","--security-opt","no-new-privileges",
        "--pids-limit",str(PIDS),"--memory",MEMORY,"--cpus",CPUS,
        "--user","65532:65532","--tmpfs","/tmp:rw,noexec,nosuid,size=64m",
        IMAGE,"python","-I","-",
    ]
    try:
        result=subprocess.run(cmd,input=req.code,capture_output=True,text=True,timeout=TIMEOUT+2)
        return {"output":trunc(result.stdout),"error":trunc(result.stderr),
                "timed_out":False,"return_code":result.returncode}
    except FileNotFoundError as exc:
        raise HTTPException(503,"Docker daemon is unavailable.") from exc
    except subprocess.TimeoutExpired:
        subprocess.run(["docker","rm","-f",name],capture_output=True,text=True,timeout=5)
        return {"output":"","error":"Execution timed out; container was terminated.",
                "timed_out":True,"return_code":-1}
