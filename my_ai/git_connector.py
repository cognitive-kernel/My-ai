from __future__ import annotations
import base64, os
from urllib.parse import urlparse
import httpx

class GitHubConnector:
    """Explicit GitHub repository connector. Reads by default; writes require allow_write=True."""
    def __init__(self, token: str | None = None, api_url: str | None = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.api_url = (api_url or os.getenv("GITHUB_API_URL") or "https://api.github.com").rstrip("/")
        self.timeout = float(os.getenv("MYAI_GITHUB_TIMEOUT", "15"))

    def _headers(self):
        h={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
        if self.token: h["Authorization"]="Bearer "+self.token
        return h

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
            raise ValueError(f"GitHub API {r.status_code}: {r.text[:500]}")
        return r.json() if r.content else {}

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
