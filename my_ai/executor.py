from __future__ import annotations
import os,subprocess,sys,tempfile
from dataclasses import dataclass
from pathlib import Path
from .config import settings
@dataclass(frozen=True)
class ExecutionResult: output:str; error:str; timed_out:bool; return_code:int
def run_python(code):
    with tempfile.TemporaryDirectory(prefix="myai-") as tmp:
        p=Path(tmp)/"main.py"; p.write_text(code,encoding="utf-8")
        try:
            r=subprocess.run([sys.executable,"-I",str(p)],cwd=tmp,capture_output=True,text=True,timeout=settings.exec_timeout,env={"PATH":os.environ.get("PATH","")})
            return ExecutionResult(r.stdout[-12000:],r.stderr[-12000:],False,r.returncode)
        except subprocess.TimeoutExpired:return ExecutionResult("","Execution timed out.",True,-1)
