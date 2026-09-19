from __future__ import annotations
import base64, os, shutil, subprocess, threading, time, webbrowser
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
    _oauth_pending = None
    _gcm_pending = None
    _oauth_lock = threading.Lock()
    _gcm_lock = threading.Lock()
    """Explicit GitHub repository connector. Reads by default; writes require allow_write=True."""
    def __init__(self, token: str | None = None, api_url: str | None = None):
        self._explicit_token = token
        self.api_url = (api_url or os.getenv("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
        self.timeout = float(os.getenv("MYAI_GITHUB_TIMEOUT", "15"))

    @staticmethod
    def _token_path():
        configured = os.getenv("MYAI_GITHUB_TOKEN_FILE")
        if configured:
            path = Path(configured).expanduser()
            if path.is_absolute():
                return path
            return Path(__file__).resolve().parent.parent / path
        return Path(__file__).resolve().parent.parent / "data" / ".github_token"

    @classmethod
    def _saved_token(cls):
        try:
            p = cls._token_path()
            return p.read_text(encoding="utf-8").strip() or None if p.exists() else None
        except OSError:
            return None

    @classmethod
    def save_token(cls, token):
        token = token.strip()
        p = cls._token_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        if token:
            p.write_text(token, encoding="utf-8")
            try: os.chmod(p, 0o600)
            except OSError: pass
        elif p.exists():
            p.unlink()
        return bool(token)

    @staticmethod
    def _gh_executable():
        return shutil.which("gh") or shutil.which("gh.exe")

    @staticmethod
    def _git_executable():
        return shutil.which("git") or shutil.which("git.exe")

    @classmethod
    def gh_available(cls): return bool(cls._gh_executable())

    @classmethod
    def gcm_available(cls):
        git = cls._git_executable()
        if not git: return False
        try:
            r = subprocess.run([git, "credential-manager", "--version"], capture_output=True, text=True, timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.returncode == 0: return True
            r = subprocess.run([git, "credential-manager-core", "--version"], capture_output=True, text=True, timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return r.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    @classmethod
    def _gcm_token(cls):
        git = cls._git_executable()
        if not git: return None
        env = os.environ.copy()
        env["GCM_GUI_PROMPT"] = "false"
        env["GCM_INTERACTIVE"] = "never"
        payload = "protocol=https\nhost=github.com\n\n"
        try:
            r = subprocess.run([git, "credential", "fill"], input=payload, capture_output=True, text=True, timeout=5, env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.returncode != 0: return None
            values = {}
            for line in r.stdout.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1); values[k] = v
            return values.get("password") or None
        except (OSError, subprocess.SubprocessError):
            return None

    @classmethod
    def gcm_login(cls):
        git = cls._git_executable()
        if not git: raise RuntimeError("Git نصب نیست.")
        if not cls.gcm_available(): raise RuntimeError("Git Credential Manager نصب/فعال نیست. Git for Windows را به‌روز کنید.")
        with cls._gcm_lock:
            if cls._gcm_pending and cls._gcm_pending.poll() is None:
                return {"pending": True}
            env = os.environ.copy()
            env["GCM_GUI_PROMPT"] = "true"
            env["GCM_INTERACTIVE"] = "auto"
            proc = subprocess.Popen(
                [git, "-c", "credential.interactive=auto", "ls-remote", "https://github.com/cognitive-kernel/My-ai.git", "HEAD"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), start_new_session=(os.name != "nt"),
            )
            cls._gcm_pending = proc
        return {"pending": True}

    @classmethod
    def gcm_status(cls):
        token = cls._gcm_token()
        with cls._gcm_lock:
            proc = cls._gcm_pending
            if proc is not None and proc.poll() is not None:
                cls._gcm_pending = None
        if token: return {"status": "authenticated", "token_source": "git_credential_manager"}
        if proc is not None and proc.poll() is None: return {"status": "pending"}
        return {"status": "none"}

    @classmethod
    def oauth_client_id(cls): return (os.getenv("MYAI_GITHUB_CLIENT_ID") or os.getenv("GITHUB_CLIENT_ID") or "").strip()
    @classmethod
    def oauth_available(cls): return bool(cls.oauth_client_id() or cls._saved_token() or cls._gcm_token() or os.getenv("GITHUB_TOKEN"))

    @classmethod
    def oauth_start(cls):
        client_id = cls.oauth_client_id()
        if not client_id: raise RuntimeError("برای OAuth داخلی GitHub باید MYAI_GITHUB_CLIENT_ID تنظیم شود؛ یا Git Credential Manager/یک GitHub token در دسترس باشد.")
        with cls._oauth_lock:
            now = time.time()
            if cls._oauth_pending and cls._oauth_pending.get("expires_at", 0) > now:
                return {k: cls._oauth_pending[k] for k in ("verification_uri", "user_code", "expires_in", "interval")}
            with httpx.Client(timeout=15, follow_redirects=False) as c:
                r = c.post("https://github.com/login/device/code", headers={"Accept": "application/json"}, data={"client_id": client_id, "scope": "repo read:user"})
            if r.status_code >= 400:
                try: body = r.json()
                except ValueError: body = {}
                raise RuntimeError(str(body.get("error_description") or body.get("error") or r.text[:300] or "GitHub OAuth device flow failed"))
            try: data = r.json()
            except ValueError: raise RuntimeError("GitHub OAuth پاسخ JSON معتبری برنگرداند.")
            device_code = data.get("device_code")
            if not device_code or not data.get("user_code") or not data.get("verification_uri"): raise RuntimeError("GitHub OAuth پاسخ معتبری برنگرداند.")
            interval = max(5, int(data.get("interval", 5))); expires_in = int(data.get("expires_in", 900))
            cls._oauth_pending = {"device_code": device_code, "user_code": data["user_code"], "verification_uri": data["verification_uri"], "expires_in": expires_in, "interval": interval, "expires_at": time.time()+expires_in, "next_poll_at": time.time()}
            result = {k: cls._oauth_pending[k] for k in ("verification_uri", "user_code", "expires_in", "interval")}
        try: webbrowser.open(result["verification_uri"])
        except Exception: pass
        return result

    @classmethod
    def oauth_poll(cls):
        with cls._oauth_lock:
            pending = cls._oauth_pending
            if not pending: return {"status": "none"}
            now = time.time()
            if now >= pending["expires_at"]: cls._oauth_pending=None; return {"status":"expired"}
            if now < pending.get("next_poll_at",0): return {"status":"pending"}
            pending["next_poll_at"] = now + pending["interval"]; client_id=pending["device_code"] and cls.oauth_client_id(); device_code=pending["device_code"]
        with httpx.Client(timeout=15, follow_redirects=False) as c:
            r=c.post("https://github.com/login/oauth/access_token",headers={"Accept":"application/json"},data={"client_id":client_id,"device_code":device_code,"grant_type":"urn:ietf:params:oauth:grant-type:device_code"})
        try: data=r.json()
        except ValueError: data={}
        if data.get("access_token"):
            cls.save_token(data["access_token"])
            with cls._oauth_lock: cls._oauth_pending=None
            return {"status":"authenticated","token_source":"saved"}
        error=data.get("error")
        if error=="authorization_pending": return {"status":"pending"}
        if error=="slow_down":
            with cls._oauth_lock:
                if cls._oauth_pending: cls._oauth_pending["interval"]=max(cls._oauth_pending.get("interval",5)+5,int(data.get("interval",0) or 0))
            return {"status":"pending"}
        with cls._oauth_lock: cls._oauth_pending=None
        return {"status":"error","error":str(data.get("error_description") or error or r.text[:300] or "GitHub OAuth failed")}

    @classmethod
    def oauth_status(cls): return cls.oauth_poll()
    @classmethod
    def gh_logged_in(cls):
        exe=cls._gh_executable()
        if not exe:return False
        try:
            r=subprocess.run([exe,"auth","status","--hostname","github.com"],capture_output=True,text=True,timeout=8,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)); return r.returncode==0
        except (OSError,subprocess.SubprocessError): return False
    @classmethod
    def gh_login(cls):
        exe=cls._gh_executable()
        if not exe: raise RuntimeError("GitHub CLI (gh) نصب نیست.")
        try:
            flags=getattr(subprocess,"CREATE_NO_WINDOW",0)
            if os.name=="nt": flags|=getattr(subprocess,"DETACHED_PROCESS",0)
            subprocess.Popen([exe,"auth","login","--hostname","github.com","--web","--git-protocol","https"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,creationflags=flags,start_new_session=(os.name!="nt")); return cls.gh_logged_in()
        except (OSError,subprocess.SubprocessError) as exc: raise RuntimeError(f"اجرای ورود GitHub ناموفق بود: {exc}") from exc
    @classmethod
    def gh_token(cls):
        exe=cls._gh_executable()
        if not exe or not cls.gh_logged_in(): return None
        try:
            r=subprocess.run([exe,"auth","token","--hostname","github.com"],capture_output=True,text=True,timeout=8,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0)); return r.stdout.strip() if r.returncode==0 and r.stdout.strip() else None
        except (OSError,subprocess.SubprocessError): return None
    @classmethod
    def token_source(cls):
        if cls.gh_logged_in(): return "github_cli_oauth"
        if cls._saved_token(): return "saved"
        if cls._gcm_token(): return "git_credential_manager"
        if os.getenv("GITHUB_TOKEN"): return "environment"
        return "none"
    @classmethod
    def token_status(cls): return cls.token_source()!="none"
    def _effective_token(self):
        explicit=getattr(self,"_explicit_token",None)
        if explicit is not None:return explicit
        return self.gh_token() or self._saved_token() or self._gcm_token() or os.getenv("GITHUB_TOKEN")
    def _headers(self):
        h={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"My-AI-GitHub-Connector"}; token=self._effective_token()
        if token:h["Authorization"]="Bearer "+token
        return h
    def token_diagnostics(self):
        token=self._effective_token()
        if not token:return {"present":False,"length":0,"prefix":"","suffix":"","kind":"none"}
        t=token.strip(); kind="fine_grained" if t.startswith("github_pat_") else ("legacy_or_app" if t.startswith(("ghp_","gho_","ghu_","ghs_","ghr_")) else "unknown")
        return {"present":True,"length":len(t),"prefix":t[:11],"suffix":t[-4:],"kind":kind}
    @staticmethod
    def parse_repo(value: str):
        value=value.strip().rstrip("/")
        if value.startswith("git@github.com:"): value=value.split(":",1)[1]
        elif value.startswith(("https://","http://")):
            p=urlparse(value)
            if p.netloc.lower() not in {"github.com","www.github.com"}: raise ValueError("Only GitHub repositories are supported by this connector.")
            value=p.path.lstrip("/")
        value=value.removesuffix(".git"); parts=value.split("/")
        if len(parts)!=2 or not all(parts): raise ValueError("Repository must be owner/name or a GitHub repository URL.")
        return parts[0],parts[1]
    def _request(self,method,path,**kwargs):
        with httpx.Client(timeout=self.timeout,follow_redirects=False) as c:r=c.request(method,self.api_url+path,headers=self._headers(),**kwargs)
        if r.status_code>=400:
            try:body=r.json()
            except ValueError:body={}
            message=str(body.get("message") or r.text[:500] or "GitHub API request failed"); raise GitHubAPIError(r.status_code,message,headers=r.headers,body=body)
        return r.json() if r.content else {}
    def whoami(self):return self._request("GET","/user")
    def repo(self,repository):
        owner,name=self.parse_repo(repository); return self._request("GET",f"/repos/{owner}/{name}")
    def tree(self,repository,ref="HEAD",recursive=True):
        owner,name=self.parse_repo(repository); data=self._request("GET",f"/repos/{owner}/{name}/git/trees/{ref}",params={"recursive":"1" if recursive else "0"}); return data.get("tree",[])
    def file(self,repository,path,ref=None):
        owner,name=self.parse_repo(repository); params={"ref":ref} if ref else {}; data=self._request("GET",f"/repos/{owner}/{name}/contents/{path.lstrip('/')}",params=params)
        if isinstance(data,list):return {"type":"directory","items":data}
        content=data.get("content","")
        if data.get("encoding")=="base64":content=base64.b64decode(content).decode("utf-8",errors="replace")
        return {"path":data.get("path"),"sha":data.get("sha"),"content":content,"html_url":data.get("html_url")}
    def issues(self,repository,state="open",limit=30):
        owner,name=self.parse_repo(repository); return self._request("GET",f"/repos/{owner}/{name}/issues",params={"state":state,"per_page":min(limit,100)})
    def pull_requests(self,repository,state="open",limit=30):
        owner,name=self.parse_repo(repository); return self._request("GET",f"/repos/{owner}/{name}/pulls",params={"state":state,"per_page":min(limit,100)})
    def branches(self,repository,limit=100):
        owner,name=self.parse_repo(repository); return self._request("GET",f"/repos/{owner}/{name}/branches",params={"per_page":min(limit,100)})
    def create_branch(self,repository,branch,base="main",allow_write=False):
        if not allow_write:raise PermissionError("GitHub writes require allow_write=True.")
        owner,name=self.parse_repo(repository); ref=self._request("GET",f"/repos/{owner}/{name}/git/ref/heads/{base}"); return self._request("POST",f"/repos/{owner}/{name}/git/refs",json={"ref":"refs/heads/"+branch,"sha":ref["object"]["sha"]})
    def update_file(self,repository,path,content,message,branch="main",allow_write=False):
        if not allow_write:raise PermissionError("GitHub writes require allow_write=True.")
        owner,name=self.parse_repo(repository)
        try:current=self.file(repository,path,branch)
        except ValueError:current={}
        payload={"message":message,"content":base64.b64encode(content.encode()).decode(),"branch":branch}
        if current.get("sha"):payload["sha"]=current["sha"]
        return self._request("PUT",f"/repos/{owner}/{name}/contents/{path.lstrip('/')}",json=payload)
