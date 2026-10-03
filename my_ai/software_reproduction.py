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


def analyze_source(source: str) -> dict[str, Any]:
    text = str(source or "").strip()
    if not text:
        raise ValueError("A URL, repository, archive, or local project path is required.")
    if urlparse(text).scheme in {"http", "https"}:
        return build_reproduction_spec(analyze_url(text))
    raise ValueError("This analyzer currently accepts authorized public HTTP/HTTPS sources; repository/archive/local adapters are added as separate capabilities.")
