from __future__ import annotations

import logging
logger = logging.getLogger(__name__)

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from .access_policy import assert_mutation_allowed
from .db import execute, fetch_all
from .llm import OllamaClient

TEXT_EXTENSIONS={".py",".php",".js",".ts",".jsx",".tsx",".html",".htm",".css",".sql",".json",".yml",".yaml",".env",".ini",".conf",".toml"}
SKIP_DIRS={".git",".venv","venv","node_modules","__pycache__","dist","build",".pytest_cache",".mypy_cache"}
_SECRET_VALUE=re.compile(r"""(?i)(api[_-]?key|secret|password|passwd|token)[ ]*([:=])[ ]*("([^"]+)"|'([^']+)')""")

@dataclass
class Finding:
    severity:str
    title:str
    file:str
    line:int
    evidence:str
    remediation:str
    rule_id:str

RULES=[
    ("critical","Hard-coded secret","secret",r"(?i)(api[_-]?key|secret|password|passwd|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]","Move secrets to environment/secret storage and rotate exposed credentials."),
    ("high","Dynamic code execution","code-exec",r"(?i)\b(eval|exec)\s*\(","Avoid dynamic execution of untrusted input; use explicit parsing/dispatch."),
    ("high","Shell command injection risk","shell-injection",r"(?i)subprocess\.(run|Popen|call|check_output)\([^\n]*shell\s*=\s*True","Use argument arrays and avoid shell=True for user-controlled data."),
    ("high","Weak password hashing","weak-hash",r"(?i)\b(md5|sha1)\s*\(","Use a password hashing function such as Argon2id/bcrypt/PBKDF2; hashes for integrity are different."),
    ("high","SQL injection risk","sql-injection",r"(?i)(execute|executemany)\s*\(\s*(f['\"]|['\"][^'\"]*%s|['\"][^'\"]*\+)","Use parameterized queries and bind variables."),
    ("medium","Debug mode enabled","debug-mode",r"(?i)\bdebug\s*=\s*True\b|\bapp\.run\([^\n]*debug\s*=\s*True","Disable debug mode in production."),
    ("medium","Permissive CORS","cors-wildcard",r"(?i)allow_origins\s*=\s*\[\s*['\"]\*['\"]\s*\]","Restrict CORS origins to trusted application origins."),
    ("medium","Dangerous HTML injection sink","xss-sink",r"(?i)\.(innerHTML|outerHTML)\s*=","Prefer textContent or safe templating and encode untrusted output."),
    ("medium","Path traversal risk","path-traversal",r"(?i)(open|read_text|write_text|send_file|FileResponse)\s*\([^\n]*(request|query|params|filename|path)","Validate and constrain user-supplied paths to an intended directory."),
    ("medium","Plaintext password storage","plaintext-password",r"(?i)(password|passwd)\s*[:=]\s*[^#\n]*(str|text|varchar|TEXT|VARCHAR)","Store password hashes, never plaintext passwords."),
]

_COMPILED_RULES=[(severity,title,rule_id,re.compile(pattern),remediation) for severity,title,rule_id,pattern,remediation in RULES]

class SecurityEngine:
    def __init__(self,llm=None):
        self.llm=llm or OllamaClient()

    def _files(self, project_path:str):
        root=Path(project_path).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError("project_path must be an existing directory")
        files=[]
        for p in root.rglob("*"):
            if not p.is_file() or p.name.lower() == ".env" or p.suffix.lower() not in TEXT_EXTENSIONS:
                continue
            if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
                continue
            try:
                if p.stat().st_size <= 500_000:
                    files.append(p)
            except OSError as exc:
                logger.debug("SECURITY_FILE_STAT_FAILED path=%s error=%s", p, exc)
        return root,files

    def scan_path(self,project_path:str,fix:bool=False):
        if fix: assert_mutation_allowed("security remediation")
        root,files=self._files(project_path)
        findings=[]
        for path in files:
            try: text=path.read_text(encoding="utf-8",errors="ignore")
            except OSError: continue
            lines=text.splitlines()
            rel=str(path.relative_to(root))
            for severity,title,rule_id,pattern,remediation in _COMPILED_RULES:
                for no,line in enumerate(lines,1):
                    if pattern.search(line):
                        findings.append(Finding(severity,title,rel,no,self._redact_evidence(line.strip()[:300]),remediation,rule_id))
        findings.extend(self._structural_checks(files))
        result={"project_path":str(root),"findings":[f.__dict__ for f in findings],"summary":self._summary(findings),"fixed":False}
        scan_id=execute("INSERT INTO security_scans(project_path,status,summary,findings) VALUES(?,?,?,?)",
                         (str(root),"completed",json.dumps(result["summary"],ensure_ascii=False),json.dumps(result["findings"],ensure_ascii=False)))
        result["scan_id"]=scan_id
        if fix and findings:
            result.update(self._fix_path(root,findings))
        return result

    def scan_code(self,code:str,language:str="Python",fix:bool=False):
        if fix: assert_mutation_allowed("security remediation")
        findings=[]
        for severity,title,rule_id,pattern,remediation in _COMPILED_RULES:
            for no,line in enumerate(code.splitlines(),1):
                if pattern.search(line):
                    findings.append(Finding(severity,title,"<generated>",no,self._redact_evidence(line.strip()[:300]),remediation,rule_id))
        result={"language":language,"findings":[f.__dict__ for f in findings],"summary":self._summary(findings),"fixed":False,"code":code}
        if fix and findings:
            result.update(self._fix_code(code,language,findings))
        return result

    def _structural_checks(self,files):
        names={p.name.lower() for p in files}
        if any(n in names for n in ("requirements.txt","pyproject.toml","package.json","composer.json")):
            return []
        return [Finding("low","No dependency manifest detected","dependency-manifest",0,
                         "No common dependency manifest was found.",
                         "Declare dependencies explicitly and keep them reviewed and updated.","dependency-manifest")]

    @staticmethod
    def _redact_evidence(line:str) -> str:
        return _SECRET_VALUE.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", line)

    def _summary(self,findings):
        return {level:sum(1 for f in findings if f.severity==level) for level in ("critical","high","medium","low")}

    def _fix_code(self,code,language,findings):
        prompt=("Fix ONLY the identified security findings in this source code. Preserve behavior and public interfaces. "
                "Return ONLY source code.\n"
                f"LANGUAGE: {language}\nFINDINGS:{json.dumps([f.__dict__ for f in findings],ensure_ascii=False)}\nCODE:\n{code}")
        fixed=self.llm.chat(prompt,system="You are a secure code remediation engineer. Return source code only.").strip()
        fence=chr(96)*3
        if fixed.startswith(fence):
            parts=fixed.splitlines()[1:]
            if parts and parts[-1].strip()==fence: parts=parts[:-1]
            fixed="\n".join(parts).strip()
        return {"fixed":True,"fixed_code":fixed,"post_scan":self.scan_code(fixed,language,False)}

    def _fix_path(self,root,findings):
        assert_mutation_allowed("security remediation")
        backup=root.parent/(root.name+".myai-backup")
        if backup.exists(): shutil.rmtree(backup)
        shutil.copytree(root,backup)
        changed=[]
        by_file={}
        for f in findings:
            if f.file!="<generated>" and f.line:
                by_file.setdefault(f.file,[]).append(f)
        for rel,fs in by_file.items():
            path=root/rel
            try: original=path.read_text(encoding="utf-8")
            except OSError: continue
            prompt=("Fix ONLY these security findings in this file. Preserve behavior. Return ONLY the full file content.\n"
                    f"FILE: {rel}\nFINDINGS:{json.dumps([x.__dict__ for x in fs],ensure_ascii=False)}\nCONTENT:\n{original}")
            fixed=self.llm.chat(prompt,system="You are a secure code remediation engineer. Return the complete file only.").strip()
            fence=chr(96)*3
            if fixed.startswith(fence):
                parts=fixed.splitlines()[1:]
                if parts and parts[-1].strip()==fence: parts=parts[:-1]
                fixed="\n".join(parts).strip()
            if fixed and fixed!=original:
                path.write_text(fixed,encoding="utf-8"); changed.append(rel)
        post=self.scan_path(str(root),False)
        return {"fixed":True,"backup_path":str(backup),"changed_files":changed,"post_scan":post}

    def history(self,limit:int=20):
        return fetch_all("SELECT * FROM security_scans ORDER BY id DESC LIMIT ?",(max(1,min(limit,100)),))
