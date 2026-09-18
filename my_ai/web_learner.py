from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .config import settings


class WebLearner:
    def fetch(self, url: str) -> tuple[str, str]:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Only valid HTTP/HTTPS URLs are allowed.")

        response = httpx.get(
            url,
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "My-AI/0.1 (+local-learning-agent)"},
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            raise ValueError("The URL does not appear to contain text/HTML.")

        soup = BeautifulSoup(response.text, "html.parser")
        for node in soup(["script", "style", "noscript", "svg"]):
            node.decompose()

        title = soup.title.get_text(" ", strip=True) if soup.title else url
        text = soup.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return title, text[: settings.max_web_chars]
