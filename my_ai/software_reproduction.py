from __future__ import annotations

from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse
from typing import Any
import re
import ipaddress
import socket

import httpx
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class Evidence:
    url: str
    kind: str
    value: str
    source: str = "authorized_public_fetch"


def _validate_url(url: str) -> str:
    parsed = urlparse(str(url).strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not parsed.hostname:
        raise ValueError("Only http/https URLs are supported.")
    host = parsed.hostname
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, None)}
        except OSError as exc:
            raise ValueError("Unable to resolve source host.") from exc
    if any(addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_multicast or addr.is_reserved for addr in addresses):
        raise ValueError("Private, loopback, link-local, multicast, and reserved hosts are not valid public analysis targets.")
    return parsed.geturl()


def analyze_url(url: str, *, timeout: float = 15.0) -> dict[str, Any]:
    target = _validate_url(url)
    headers = {"User-Agent": "My-AI/1.0 authorized-analysis"}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = client.get(target)
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    links = []
    for tag in soup.find_all("a", href=True):
        href = urljoin(str(response.url), str(tag.get("href")))
        if urlparse(href).scheme in {"http", "https"}:
            links.append(href)
    forms = []
    for form in soup.find_all("form"):
        fields = []
        for field in form.find_all(["input", "select", "textarea", "button"]):
            fields.append({
                "tag": field.name,
                "name": field.get("name"),
                "type": field.get("type"),
                "required": field.has_attr("required"),
            })
        forms.append({
            "method": str(form.get("method") or "get").upper(),
            "action": urljoin(str(response.url), str(form.get("action") or response.url)),
            "fields": fields,
        })
    assets = {
        "scripts": [urljoin(str(response.url), str(x.get("src"))) for x in soup.find_all("script", src=True)],
        "styles": [urljoin(str(response.url), str(x.get("href"))) for x in soup.find_all("link", href=True) if "stylesheet" in str(x.get("rel") or [])],
        "images": [urljoin(str(response.url), str(x.get("src"))) for x in soup.find_all("img", src=True)],
    }
    headings = [{"level": int(tag.name[1]), "text": " ".join(tag.stripped_strings)} for tag in soup.find_all(re.compile(r"^h[1-6]$"))]
    title = " ".join(soup.title.stripped_strings) if soup.title else ""
    meta = {}
    for tag in soup.find_all("meta"):
        key = tag.get("name") or tag.get("property")
        if key and tag.get("content") is not None:
            meta[str(key)] = str(tag.get("content"))
    return {
        "url": target,
        "final_url": str(response.url),
        "status_code": response.status_code,
        "title": title,
        "headings": headings[:100],
        "links": list(dict.fromkeys(links))[:500],
        "forms": forms[:100],
        "assets": {k: list(dict.fromkeys(v))[:200] for k, v in assets.items()},
        "meta": dict(list(meta.items())[:200]),
        "html_bytes": len(response.content),
        "evidence": [asdict(Evidence(target, "html", "public page response"))],
    }


def build_reproduction_spec(analysis: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": {
            "url": analysis.get("url"),
            "final_url": analysis.get("final_url"),
            "evidence": analysis.get("evidence", []),
        },
        "requirements": {
            "routes": [analysis.get("final_url")],
            "navigation_links": analysis.get("links", []),
            "forms": analysis.get("forms", []),
            "content_structure": analysis.get("headings", []),
        },
        "ui": {
            "title": analysis.get("title", ""),
            "responsive": True,
            "assets": analysis.get("assets", {}),
            "meta": analysis.get("meta", {}),
        },
        "architecture": {
            "frontend": "componentized",
            "backend": "contract-driven",
            "data_flow": "to be inferred from authorized API/repository evidence",
            "unknowns": [
                "Private APIs, authentication flows, server-side code, database schema and protected assets require authorized evidence."
            ],
        },
        "verification": {
            "required": [
                "route/component coverage",
                "interaction and validation coverage",
                "visual comparison",
                "build/lint/unit/integration/E2E verification",
                "difference report with evidence",
            ],
            "exact_match_claim": False,
        },
    }


def _crawl_site(url: str, *, max_pages: int = 8, timeout: float = 15.0) -> list[dict[str, Any]]:
    root = _validate_url(url)
    parsed_root = urlparse(root)
    queue = [root]
    seen: set[str] = set()
    pages: list[dict[str, Any]] = []
    while queue and len(pages) < max_pages:
        current = queue.pop(0)
        try:
            parsed = urlparse(current)
            if parsed.netloc != parsed_root.netloc or current in seen:
                continue
            seen.add(current)
            page = analyze_url(current, timeout=timeout)
            pages.append(page)
            for link in page.get("links", []):
                candidate = str(link).split("#", 1)[0]
                if urlparse(candidate).netloc == parsed_root.netloc and candidate not in seen:
                    queue.append(candidate)
        except Exception:
            continue
    return pages


def _analyze_local(path: str) -> dict[str, Any]:
    root = Path(path).expanduser().resolve()
    if not root.exists():
        raise ValueError("Local source does not exist.")
    files = [p for p in root.rglob("*") if p.is_file()][:1000] if root.is_dir() else [root]
    manifests = [str(p.relative_to(root)) for p in files if p.name.lower() in {
        "pyproject.toml", "package.json", "requirements.txt", "dockerfile",
        "docker-compose.yml", "docker-compose.yaml", "go.mod", "cargo.toml",
    }]
    return {
        "source": {"path": str(root), "kind": "local", "provenance": "authorized_local_source"},
        "files": [str(p.relative_to(root)) if p.is_relative_to(root) else p.name for p in files[:500]],
        "manifests": manifests,
        "file_count": len(files),
        "requirements": {"routes": [], "forms": [], "navigation_links": []},
        "architecture": {"frontend": "unknown", "backend": "unknown", "unknowns": ["Runtime behavior requires authorized execution."]},
        "verification": {"exact_match_claim": False},
    }


def _analyze_archive(path: str) -> dict[str, Any]:
    import tempfile
    import zipfile
    import tarfile
    archive = Path(path).expanduser().resolve()
    if not archive.is_file():
        raise ValueError("Archive does not exist.")
    with tempfile.TemporaryDirectory(prefix="myai-reproduction-") as tmp:
        target = Path(tmp)
        if zipfile.is_zipfile(archive):
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(target)
        elif tarfile.is_tarfile(archive):
            with tarfile.open(archive) as tf:
                tf.extractall(target, filter="data")
        else:
            raise ValueError("Only ZIP and TAR archives are supported.")
        result = _analyze_local(str(target))
        result["source"]["archive"] = str(archive)
        result["source"]["kind"] = "archive"
        return result


def _analyze_repository(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError("Repository adapter currently supports public GitHub repositories.")
    parts = [x for x in parsed.path.split("/") if x]
    if len(parts) < 2:
        raise ValueError("GitHub repository URL must include owner and repository.")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    import httpx
    api = f"https://api.github.com/repos/{owner}/{repo}"
    with httpx.Client(timeout=20.0, headers={"Accept": "application/vnd.github+json", "User-Agent": "My-AI-authorized-analysis"}) as client:
        meta = client.get(api)
        meta.raise_for_status()
        tree = client.get(f"{api}/git/trees/{meta.json().get('default_branch', 'main')}?recursive=1")
        tree.raise_for_status()
    items = tree.json().get("tree", [])
    files = [str(x.get("path")) for x in items if x.get("type") == "blob"]
    manifests = [x for x in files if Path(x).name.lower() in {
        "pyproject.toml", "package.json", "requirements.txt", "dockerfile",
        "docker-compose.yml", "docker-compose.yaml", "go.mod", "cargo.toml",
    }]
    return {
        "source": {"url": url, "kind": "repository", "provenance": "authorized_public_repository"},
        "repository": {"owner": owner, "name": repo, "default_branch": meta.json().get("default_branch")},
        "files": files[:2000],
        "manifests": manifests,
        "file_count": len(files),
        "requirements": {"routes": [], "forms": [], "navigation_links": []},
        "architecture": {"frontend": "to be inferred from repository files", "backend": "to be inferred from repository files"},
        "verification": {"exact_match_claim": False},
    }


def analyze_source(source: str) -> dict[str, Any]:
    text = str(source or "").strip()
    if not text:
        raise ValueError("A URL, repository, archive, or local project path is required.")
    if urlparse(text).scheme in {"http", "https"}:
        parsed = urlparse(text)
        if parsed.netloc.lower() in {"github.com", "www.github.com"} and len([x for x in parsed.path.split("/") if x]) >= 2:
            return _analyze_repository(text)
        pages = _crawl_site(text)
        primary = build_reproduction_spec(pages[0]) if pages else build_reproduction_spec(analyze_url(text))
        primary["discovery"] = {"pages_analyzed": len(pages), "pages": pages}
        return primary
    path = Path(text).expanduser()
    if path.suffix.lower() in {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz"}:
        return _analyze_archive(text)
    return _analyze_local(text)
