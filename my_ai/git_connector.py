from __future__ import annotations
import base64, os
from pathlib import Path
from urllib.parse import urlparse
import httpx

class GitHubAPIError(ValueError):
    def __init__(self, status_code, message, *, headers=None, body=None):
        self.status_code = status_code
        self.message = message
        self.headers = dict(headers or {})
        self.body = body if isinstance(body, dict) else {}
        super().__init__(f"GitHub API {status_code}: {message}")

class GitHubConnector:
    """Explicit GitHub repository connector. Reads by default; writes require allow_write=True."""
    def __init__(self, token: str | None = None, api_url: str | None = None):
        # The token explicitly supplied by the caller wins. Otherwise prefer the\n        # token saved through the UI, then fall back to the environment token.\n        # This prevents an unrelated GITHUB_TOKEN from overriding a valid UI token.\n        self._explicit_token = token
        self.api_url = (api_url or os.getenv("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
        self.timeout = float(os.getenv("MYAI_GITHUB_TIMEOUT", "15"))

    @staticmethod
    def _token_path():
        return Path(os.getenv("MYAI_GITHUB_TOKEN_FILE", "data/.github_token"))

    @classmethod
    def _saved_token(cls):
        try:
            p=cls._token_path()
            return p.read_text(encoding="utf-8").strip() or None if p.exists() else None
        except OSError:
            return None

    @classmethod
    def save_token(cls, token):
        token=token.strip()
        p=cls._token_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        if token:
            p.write_text(token,encoding="utf-8")
            try: os.chmod(p,0o600)
            except OSError: pass
        elif p.exists():
            p.unlink()
        return bool(token)

    @classmethod
    def token_source(cls):
        if cls._saved_token():
            return "saved"
        if os.getenv("GITHUB_TOKEN"):
            return "environment"
        return "none"

    @classmethod
    def token_status(cls):
        return cls.token_source() != "none"

    def _effective_token(self):
        explicit = getattr(self, "_explicit_token", None)
        if explicit is not None:
            return explicit
        return self._saved_token() or os.getenv("GITHUB_TOKEN")

    def _headers(self):
        h={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"My-AI-GitHub-Connector"}
        token=self._effective_token()
        if token:
            # GitHub accepts fine-grained PATs with the Bearer scheme.
            h["Authorization"]="Bearer "+token
        return h

    def token_diagnostics(self):
        token=self._effective_token()
        if not token:
            return {"present":False,"length":0,"prefix":"","suffix":"","kind":"none"}
        t=token.strip()
        if t.startswith("github_pat_"):
            kind="fine_grained"
        elif t.startswith(("ghp_","gho_","ghu_","ghs_","ghr_")):
            kind="legacy_or_app"
        else:
            kind="unknown"
        return {
            "present":True,
            "length":len(t),
            "prefix":t[:11],
            "suffix":t[-4:],
            "kind":kind,
        }

    @staticmethod
    def parse_repo(value: str):
        value=value.strip().rstrip("/")
        if value.startswith("git@github.com:"):
            value=value.split(":",1)[1]
        elif value.startswith("https://") or value.startswith("http://"):
            p=urlparse(value)
            if p.netloc.lower() not in {"github.com","www.github.com"}:
                raise ValueError("Only GitHub repositories are supported by this connector.")
            value=p.path.lstrip("/")
        value=value.removesuffix(".git")
        parts=value.split("/")
        if len(parts)!=2 or not all(parts):
            raise ValueError("Repository must be owner/name or a GitHub repository URL.")
        return parts[0],parts[1]

    def _request(self, method, path, **kwargs):
        with httpx.Client(timeout=self.timeout, follow_redirects=False) as c:
            r=c.request(method,self.api_url+path,headers=self._headers(),**kwargs)
        if r.status_code >= 400:
            try:
                body = r.json()
            except ValueError:
                body = {}
            message = str(body.get("message") or r.text[:500] or "GitHub API request failed")
            raise GitHubAPIError(r.status_code, message, headers=r.headers, body=body)
        return r.json() if r.content else {}

    def whoami(self):
        return self._request("GET","/user")

    def repo(self, repository):
        owner,name=self.parse_repo(repository)
        return self._request("GET",f"/repos/{owner}/{name}")

    def tree(self, repository, ref="HEAD", recursive=True):
        owner,name=self.parse_repo(repository)
        data=self._request("GET",f"/repos/{owner}/{name}/git/trees/{ref}",params={"recursive":"1" if recursive else "0"})
        return data.get("tree",[])

    def file(self, repository, path, ref=None):
        owner,name=self.parse_repo(repository)
        params={"ref":ref} if ref else {}
        data=self._request("GET",f"/repos/{owner}/{name}/contents/{path.lstrip('/')}",params=params)
        if isinstance(data,list): return {"type":"directory","items":data}
        content=data.get("content","")
        if data.get("encoding")=="base64":
            content=base64.b64decode(content).decode("utf-8",errors="replace")
        return {"path":data.get("path"),"sha":data.get("sha"),"content":content,"html_url":data.get("html_url")}

    def issues(self, repository, state="open", limit=30):
        owner,name=self.parse_repo(repository)
        return self._request("GET",f"/repos/{owner}/{name}/issues",params={"state":state,"per_page":min(limit,100)})

    def pull_requests(self, repository, state="open", limit=30):
        owner,name=self.parse_repo(repository)
        return self._request("GET",f"/repos/{owner}/{name}/pulls",params={"state":state,"per_page":min(limit,100)})

    def branches(self, repository, limit=100):
        owner,name=self.parse_repo(repository)
        return self._request("GET",f"/repos/{owner}/{name}/branches",params={"per_page":min(limit,100)})

    def create_branch(self, repository, branch, base="main", allow_write=False):
        if not allow_write: raise PermissionError("GitHub writes require allow_write=True.")
        owner,name=self.parse_repo(repository)
        ref=self._request("GET",f"/repos/{owner}/{name}/git/ref/heads/{base}")
        return self._request("POST",f"/repos/{owner}/{name}/git/refs",json={"ref":"refs/heads/"+branch,"sha":ref["object"]["sha"]})

    def update_file(self, repository, path, content, message, branch="main", allow_write=False):
        if not allow_write: raise PermissionError("GitHub writes require allow_write=True.")
        owner,name=self.parse_repo(repository)
        try: current=self.file(repository,path,branch)
        except ValueError: current={}
        payload={"message":message,"content":base64.b64encode(content.encode()).decode(),"branch":branch}
        if current.get("sha"): payload["sha"]=current["sha"]
        return self._request("PUT",f"/repos/{owner}/{name}/contents/{path.lstrip('/')}",json=payload)
