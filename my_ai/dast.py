from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from .db import execute


class LocalDAST:
    """Safe, local-only dynamic web testing for projects supplied by the user.

    The target is always bound to loopback and the scanner refuses non-loopback
    URLs. It performs lightweight discovery and non-destructive HTTP checks.
    """

    def __init__(self, timeout: float = 8.0, startup_timeout: float = 20.0):
        self.timeout = timeout
        self.startup_timeout = startup_timeout

    def _free_port(self) -> int:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            return int(s.getsockname()[1])

    def _assert_local(self, url: str) -> None:
        p = urlparse(url)
        if p.scheme not in {"http", "https"}:
            raise ValueError("DAST accepts HTTP(S) URLs only")
        host = (p.hostname or "").lower()
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("DAST is restricted to localhost targets")

    def _discover_endpoints(self, root: Path) -> list[str]:
        endpoints = {"/"}
        patterns = [
            r'@(?:app|router)\.(?:get|post|put|patch|delete|route)\(\s*["\']([^"\']+)',
            r'path\s*\(\s*["\']([^"\']+)',
            r'Route\s*\(\s*["\']([^"\']+)',
            r'\$router->(?:get|post|put|patch|delete)\(\s*["\']([^"\']+)',
            r'\b(?:get|post|put|patch|delete)\(\s*["\'](/[^"\']*)',
        ]
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".py", ".php", ".js", ".ts"}:
                continue
            if any(part in {".git", "node_modules", ".venv", "venv", "__pycache__"} for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.I):
                    value = match.group(1)
                    if value.startswith("/"):
                        endpoints.add(value.split("{")[0].split("<")[0])
        return sorted(endpoints)[:100]

    def _detect_command(self, root: Path, port: int):
        files = {p.name for p in root.iterdir() if p.is_file()}
        if "requirements.txt" in files or "pyproject.toml" in files:
            py = root / "app.py"
            main = root / "main.py"
            if py.exists():
                return ["python", str(py)], f"http://127.0.0.1:{port}"
            if main.exists():
                return ["python", str(main)], f"http://127.0.0.1:{port}"
        if "composer.json" in files or any(root.glob("*.php")):
            index = root / "index.php"
            if index.exists():
                return ["php", "-S", f"127.0.0.1:{port}", "-t", str(root)], f"http://127.0.0.1:{port}"
        if "package.json" in files:
            return ["npm", "start", "--", "--host", "127.0.0.1", "--port", str(port)], f"http://127.0.0.1:{port}"
        if (root / "index.html").exists():
            return ["python", "-m", "http.server", str(port), "--bind", "127.0.0.1"], f"http://127.0.0.1:{port}"
        raise ValueError("Could not detect a supported local web runtime")

    def _wait_ready(self, base: str) -> bool:
        deadline = time.time() + self.startup_timeout
        while time.time() < deadline:
            try:
                r = httpx.get(base + "/", timeout=1.5, follow_redirects=False)
                if r.status_code < 600:
                    return True
            except Exception:
                time.sleep(0.25)
        return False

    def _request(self, client: httpx.Client, method: str, url: str, **kwargs):
        try:
            response = client.request(method, url, **kwargs)
            return response
        except Exception as exc:
            return exc

    def _checks(self, base: str, endpoints: list[str]):
        findings = []
        seen = set()
        with httpx.Client(timeout=self.timeout, follow_redirects=False) as client:
            for endpoint in endpoints:
                url = urljoin(base.rstrip("/") + "/", endpoint.lstrip("/"))
                response = self._request(client, "GET", url)
                if isinstance(response, Exception):
                    continue
                headers = {k.lower(): v for k, v in response.headers.items()}
                if "content-security-policy" not in headers:
                    key=("headers","csp")
                    if key not in seen:
                        seen.add(key)
                        findings.append({"severity":"medium","title":"Missing Content-Security-Policy","endpoint":endpoint,
                                         "evidence":"CSP header is absent from a reachable response.",
                                         "impact":"Browser-side injection and content-loading risks are harder to contain.",
                                         "remediation":"Define a restrictive Content-Security-Policy appropriate to the application."})
                if "x-content-type-options" not in headers:
                    key=("headers","nosniff")
                    if key not in seen:
                        seen.add(key)
                        findings.append({"severity":"low","title":"Missing X-Content-Type-Options","endpoint":endpoint,
                                         "evidence":"X-Content-Type-Options is absent.",
                                         "impact":"Some browsers may perform content sniffing in cases where MIME handling is ambiguous.",
                                         "remediation":"Send X-Content-Type-Options: nosniff."})
                if "x-frame-options" not in headers and "content-security-policy" not in headers:
                    key=("headers","frame")
                    if key not in seen:
                        seen.add(key)
                        findings.append({"severity":"medium","title":"Missing clickjacking protection","endpoint":endpoint,
                                         "evidence":"Neither X-Frame-Options nor CSP frame-ancestors was observed.",
                                         "impact":"Sensitive pages may be embeddable by another origin.",
                                         "remediation":"Set X-Frame-Options or, preferably, CSP frame-ancestors as appropriate."})
                if response.status_code >= 500:
                    findings.append({"severity":"medium","title":"Server error on reachable endpoint","endpoint":endpoint,
                                     "evidence":f"GET returned HTTP {response.status_code}.",
                                     "impact":"Unhandled exceptions can expose availability problems or implementation details.",
                                     "remediation":"Inspect server logs, handle invalid inputs safely, and add regression tests."})
                text = response.text[:200_000]
                if re.search(r"(?i)(traceback \(most recent call last\)|stack trace|debug toolbar)", text):
                    findings.append({"severity":"high","title":"Runtime debug/error details exposed","endpoint":endpoint,
                                     "evidence":"Response body contains recognizable debug or stack-trace content.",
                                     "impact":"Internal paths and implementation details may be disclosed.",
                                     "remediation":"Disable debug output in production and return generic error pages."})
                # Harmless reflection probe; no exploit payloads are used.
                probe = url + ("&" if "?" in url else "?") + "myai_probe=MYAI_REFLECTION_TEST"
                reflected = self._request(client, "GET", probe)
                if not isinstance(reflected, Exception) and "MYAI_REFLECTION_TEST" in reflected.text:
                    findings.append({"severity":"low","title":"User-controlled query value reflected","endpoint":endpoint,
                                     "evidence":"A harmless unique marker was reflected into the response.",
                                     "impact":"Reflection can become an XSS issue if the application places untrusted data into an executable HTML/JS context.",
                                     "remediation":"Contextually encode output and avoid unsafe HTML/JavaScript sinks; confirm with source review."})
        return findings

    def scan_path(self, project_path: str, fix: bool = False):
        root = Path(project_path).expanduser().resolve()
        if not root.is_dir():
            raise ValueError("project_path must be an existing directory")
        port = self._free_port()
        command, base = self._detect_command(root, port)
        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")
        process = subprocess.Popen(command, cwd=str(root), env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True)
        try:
            ready = self._wait_ready(base)
            if not ready:
                output = ""
                try:
                    output = (process.stdout.read(4000) if process.stdout else "")
                except Exception:
                    pass
                return {"status":"runtime_failed","command":command,"output":output}
            endpoints = self._discover_endpoints(root)
            findings = self._checks(base, endpoints)
            result = {
                "status":"completed",
                "target":base,
                "runtime":command,
                "endpoints":endpoints,
                "findings":findings,
                "summary":self._summary(findings),
                "fixed":False,
            }
            execute("INSERT INTO security_scans(project_path,status,summary,findings) VALUES(?,?,?,?)",
                    (str(root),"dast_completed",json.dumps(result["summary"],ensure_ascii=False),json.dumps(findings,ensure_ascii=False)))
            return result
        finally:
            try:
                process.terminate()
                process.wait(timeout=3)
            except Exception:
                try: process.kill()
                except Exception: pass

    def _summary(self, findings):
        return {level: sum(1 for x in findings if x["severity"] == level) for level in ("critical","high","medium","low")}
