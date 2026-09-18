from __future__ import annotations
import os, subprocess, sys, tempfile, uuid
from dataclasses import dataclass
from pathlib import Path
from .config import settings
@dataclass(frozen=True)
class ExecutionResult:
    output:str; error:str; timed_out:bool; return_code:int; sandbox_mode:str="container"
def _truncate(value:str)->str: return (value or "")[-settings.exec_output_chars:]
def _run_subprocess(code:str)->ExecutionResult:
    with tempfile.TemporaryDirectory(prefix="myai-") as tmp:
        p=Path(tmp)/"main.py"; p.write_text(code,encoding="utf-8"); os.chmod(tmp,0o755); os.chmod(p,0o644)
        try:
            r=subprocess.run([sys.executable,"-I",str(p)],cwd=tmp,capture_output=True,text=True,timeout=settings.exec_timeout,env={"PATH":os.environ.get("PATH","")})
            return ExecutionResult(_truncate(r.stdout),_truncate(r.stderr),False,r.returncode,"subprocess")
        except subprocess.TimeoutExpired:return ExecutionResult("","Execution timed out.",True,-1,"subprocess")
def _run_container(code:str)->ExecutionResult:
    name=f"myai-exec-{uuid.uuid4().hex[:16]}"
    with tempfile.TemporaryDirectory(prefix="myai-exec-") as tmp:
        p=Path(tmp)/"main.py"; p.write_text(code,encoding="utf-8"); os.chmod(tmp,0o755); os.chmod(p,0o644)
        cmd=["docker","run","--rm","--name",name,"--network","none","--read-only","--cap-drop","ALL","--security-opt","no-new-privileges","--pids-limit",str(settings.exec_pids),"--memory",settings.exec_memory,"--cpus",settings.exec_cpus,"--user","65532:65532","--tmpfs","/tmp:rw,noexec,nosuid,size=64m","--mount",f"type=bind,src={tmp},dst=/work,readonly",settings.exec_image,"python","-I","/work/main.py"]
        try:
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=settings.exec_timeout+2)
            return ExecutionResult(_truncate(r.stdout),_truncate(r.stderr),False,r.returncode,"container")
        except FileNotFoundError as e: raise RuntimeError("Docker is required for EXECUTOR_MODE=container but was not found.") from e
        except subprocess.TimeoutExpired:
            subprocess.run(["docker","rm","-f",name],capture_output=True,text=True,timeout=5)
            return ExecutionResult("","Execution timed out; container was terminated.",True,-1,"container")
def run_python(code:str)->ExecutionResult:
    if not isinstance(code,str) or not code.strip(): return ExecutionResult("","No Python code supplied.",False,2,settings.exec_mode)
    if settings.exec_mode=="container": return _run_container(code)
    if settings.exec_mode=="subprocess": return _run_subprocess(code)
    raise ValueError("EXECUTOR_MODE must be 'container' or 'subprocess'.")
