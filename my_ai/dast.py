from __future__ import annotations
import json, os, re, socket, subprocess, tempfile, time
from pathlib import Path
from urllib.parse import urljoin, urlparse
import httpx
from .db import execute

class LocalDAST:
    """Local-only, non-destructive dynamic web testing for owned/generated projects."""
    def __init__(self, timeout:float=8.0, startup_timeout:float=20.0):
        self.timeout=timeout; self.startup_timeout=startup_timeout

    def _assert_local(self,url):
        p=urlparse(url)
        if p.scheme not in {"http","https"} or (p.hostname or "").lower() not in {"127.0.0.1","localhost","::1"}:
            raise ValueError("Target is not local.")

    def _assert_public_explicit(self,url):
        p=urlparse(url)
        if p.scheme not in {"http","https"} or not p.hostname:
            raise ValueError("Target URL must be http:// or https://.")
        try:
            import ipaddress
            ip=ipaddress.ip_address(socket.gethostbyname(p.hostname))
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                raise ValueError("Public DAST target must resolve to a public address.")
        except socket.gaierror as e:
            raise ValueError("Target hostname could not be resolved.") from e
        return p

    def _free_port(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1",0)); return int(s.getsockname()[1])

    def _discover_endpoints(self, root:Path):
        endpoints={"/"}
        patterns=[
            r'@(?:app|router)\.(?:get|post|put|patch|delete|route)\(\s*["\']([^"\']+)',
            r'path\s*\(\s*["\']([^"\']+)',
            r'Route\s*\(\s*["\']([^"\']+)',
            r'\$router->(?:get|post|put|patch|delete)\(\s*["\']([^"\']+)',
            r'\b(?:get|post|put|patch|delete)\(\s*["\'](/[^"\']*)',
        ]
        for p in root.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in {".py",".php",".js",".ts"}: continue
            if any(x in {".git","node_modules",".venv","venv","__pycache__"} for x in p.parts): continue
            try: src=p.read_text(encoding="utf-8",errors="ignore")
            except OSError: continue
            for pat in patterns:
                for m in re.finditer(pat,src,re.I):
                    v=m.group(1)
                    if v.startswith("/"): endpoints.add(v.split("{")[0].split("<")[0])
        return sorted(endpoints)[:100]

    def _detect_command(self,root:Path,port:int):
        files={p.name for p in root.iterdir() if p.is_file()}
        if "requirements.txt" in files or "pyproject.toml" in files or (root/"app.py").exists() or (root/"main.py").exists():
            target=root/"app.py" if (root/"app.py").exists() else root/"main.py"
            src=target.read_text(encoding="utf-8",errors="ignore") if target.exists() else ""
            if re.search(r"\bFastAPI\s*\(",src) and re.search(r"\bapp\s*=\s*FastAPI",src):
                return ["uvicorn",f"{target.stem}:app","--host","127.0.0.1","--port",str(port)],f"http://127.0.0.1:{port}"
            if re.search(r"\bFlask\s*\(",src) and re.search(r"\bapp\s*=\s*Flask",src):
                return ["flask","--app",target.name,"run","--host","127.0.0.1","--port",str(port)],f"http://127.0.0.1:{port}"
            return ["python",str(target)],f"http://127.0.0.1:{port}"
        if "composer.json" in files or any(root.glob("*.php")):
            return ["php","-S",f"127.0.0.1:{port}","-t",str(root)],f"http://127.0.0.1:{port}"
        if (root/"index.html").exists():
            return ["python","-m","http.server",str(port),"--bind","127.0.0.1"],f"http://127.0.0.1:{port}"
        raise ValueError("Could not detect a supported local web runtime")

    def _wait_ready(self,base):
        deadline=time.time()+self.startup_timeout
        while time.time()<deadline:
            try:
                r=httpx.get(base+"/",timeout=1.5,follow_redirects=False)
                if r.status_code<600: return True
            except Exception: time.sleep(.25)
        return False

    def _checks(self,base,endpoints):
        findings=[]; seen=set()
        with httpx.Client(timeout=self.timeout,follow_redirects=False) as client:
            for ep in endpoints:
                url=urljoin(base.rstrip("/")+"/",ep.lstrip("/"))
                try: r=client.get(url)
                except Exception: continue
                h={k.lower():v for k,v in r.headers.items()}
                checks=[
                    ("csp","medium","Missing Content-Security-Policy","CSP header is absent.","Browser-side injection and content-loading risks are harder to contain.","Define a restrictive Content-Security-Policy."),
                    ("nosniff","low","Missing X-Content-Type-Options","X-Content-Type-Options is absent.","Some browsers may perform content sniffing.","Send X-Content-Type-Options: nosniff."),
                ]
                for key,sev,title,evidence,impact,remediation in checks:
                    if key not in seen and (("csp"==key and "content-security-policy" not in h) or ("nosniff"==key and "x-content-type-options" not in h)):
                        seen.add(key); findings.append({"severity":sev,"title":title,"endpoint":ep,"evidence":evidence,"impact":impact,"remediation":remediation})
                if "x-frame-options" not in h and "content-security-policy" not in h and "frame" not in seen:
                    seen.add("frame"); findings.append({"severity":"medium","title":"Missing clickjacking protection","endpoint":ep,"evidence":"Neither X-Frame-Options nor CSP was observed.","impact":"Sensitive pages may be embeddable by another origin.","remediation":"Set X-Frame-Options or CSP frame-ancestors."})
                if r.status_code>=500:
                    findings.append({"severity":"medium","title":"Server error on reachable endpoint","endpoint":ep,"evidence":f"GET returned HTTP {r.status_code}.","impact":"Unhandled exceptions may expose availability or implementation problems.","remediation":"Inspect logs, validate inputs and add regression tests."})
                body=r.text[:200000]
                if re.search(r"(?i)(traceback \(most recent call last\)|stack trace|debug toolbar)",body):
                    findings.append({"severity":"high","title":"Runtime debug/error details exposed","endpoint":ep,"evidence":"Response contains recognizable debug or stack-trace content.","impact":"Internal paths and implementation details may be disclosed.","remediation":"Disable debug output and return generic error pages."})
                probe=url+("&" if "?" in url else "?")+"myai_probe=MYAI_REFLECTION_TEST"
                try: rr=client.get(probe)
                except Exception: rr=None
                if rr is not None and "MYAI_REFLECTION_TEST" in rr.text:
                    findings.append({"severity":"low","title":"User-controlled query value reflected","endpoint":ep,"evidence":"A harmless unique marker was reflected.","impact":"Reflection can become XSS if placed in an executable context.","remediation":"Contextually encode output and avoid unsafe HTML/JS sinks; confirm with source review."})
        return findings

    def _crawl_public(self,base,limit=30):
        basep=urlparse(base); seen={base}; queue=[base]
        with httpx.Client(timeout=self.timeout,follow_redirects=False) as client:
            while queue and len(seen)<limit:
                cur=queue.pop(0)
                try:r=client.get(cur)
                except Exception:continue
                if "text/html" not in r.headers.get("content-type","").lower(): continue
                for href in re.findall(r'''href=["\\']([^"\\'#]+)''',r.text[:300000],re.I):
                    nxt=urljoin(cur,href)
                    p=urlparse(nxt)
                    if p.scheme not in {"http","https"} or p.netloc.lower()!=basep.netloc.lower(): continue
                    if nxt not in seen:
                        seen.add(nxt); queue.append(nxt)
        return sorted(urlparse(x).path or "/" for x in seen)[:limit]

    def scan_url(self,url:str,explicit=True):
        if not explicit: raise PermissionError("A target URL must be explicitly supplied by the user.")
        p=self._assert_public_explicit(url)
        base=p.scheme + "://" + p.netloc + (p.path or "/")
        endpoints=self._crawl_public(base); findings=self._checks(base,endpoints)
        result={"status":"completed","target":url,"mode":"explicit_external_url","endpoints":endpoints,"findings":findings,"summary":self._summary(findings),"fixed":False}
        execute("INSERT INTO security_scans(project_path,status,summary,findings) VALUES(?,?,?,?)",(url,"dast_external_completed",json.dumps(result["summary"],ensure_ascii=False),json.dumps(findings,ensure_ascii=False)))
        return result

    def _run(self,root:Path):
        port=self._free_port(); command,base=self._detect_command(root,port)
        process=subprocess.Popen(command,cwd=str(root),env=os.environ.copy(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        try:
            if not self._wait_ready(base):
                output=""
                try: output=process.stdout.read(4000) if process.stdout else ""
                except Exception: pass
                return {"status":"runtime_failed","command":command,"output":output}
            endpoints=self._discover_endpoints(root); findings=self._checks(base,endpoints)
            result={"status":"completed","target":base,"runtime":command,"endpoints":endpoints,"findings":findings,"summary":self._summary(findings),"fixed":False}
            execute("INSERT INTO security_scans(project_path,status,summary,findings) VALUES(?,?,?,?)",(str(root),"dast_completed",json.dumps(result["summary"],ensure_ascii=False),json.dumps(findings,ensure_ascii=False)))
            return result
        finally:
            try: process.terminate(); process.wait(timeout=3)
            except Exception:
                try: process.kill()
                except Exception: pass

    def scan_path(self,project_path:str):
        root=Path(project_path).expanduser().resolve()
        if not root.is_dir(): raise ValueError("project_path must be an existing directory")
        return self._run(root)

    def scan_code(self,code:str,language:str="Python"):
        lang=language.lower()
        with tempfile.TemporaryDirectory(prefix="myai-dast-") as tmp:
            root=Path(tmp)
            if lang=="php": (root/"index.php").write_text(code,encoding="utf-8")
            elif lang in {"html","htm"}: (root/"index.html").write_text(code,encoding="utf-8")
            elif lang in {"python","py"}: (root/"app.py").write_text(code,encoding="utf-8")
            else: return {"status":"unsupported","language":language,"findings":[],"summary":{"critical":0,"high":0,"medium":0,"low":0}}
            return self._run(root)

    @staticmethod
    def _summary(findings):
        return {x:sum(1 for f in findings if f["severity"]==x) for x in ("critical","high","medium","low")}
