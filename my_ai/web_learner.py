from __future__ import annotations
import re
import time
import threading
import logging
from urllib.parse import urlparse, quote_plus
from urllib import robotparser
import httpx
from bs4 import BeautifulSoup
from .config import settings
from .network import assert_public_hostname, pinned_client

logger = logging.getLogger("my_ai.web_learner")

class WebLearner:
    _rate_lock = threading.Lock()
    _last_fetch: dict[str, float] = {}
    _min_interval = 1.0

    @classmethod
    def _rate_limit(cls, host: str, stop_event=None) -> None:
        now = time.monotonic()
        with cls._rate_lock:
            previous = cls._last_fetch.get(host, 0.0)
            wait = cls._min_interval - (now - previous)
            if wait > 0:
                logger.info("web fetch rate limit wait", extra={"host": host, "wait": round(wait, 3)})
                if stop_event is not None:
                    if stop_event.wait(wait):
                        raise InterruptedError("learning stopped")
                else:
                    time.sleep(wait)
                now = time.monotonic()
            cls._last_fetch[host] = now

    def search(self,query,domains=None,limit=6):
        q=query+((" site:"+" OR site:".join(domains)) if domains else "")
        r=httpx.get("https://html.duckduckgo.com/html/?q="+quote_plus(q),timeout=20,follow_redirects=True,headers={"User-Agent":"My-AI/0.2"}); r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        return [{"title":a.get_text(" ",strip=True),"url":a.get("href")} for a in soup.select("a.result__a")[:limit] if a.get("href") and a.get_text(" ",strip=True)]
    @staticmethod
    def _safe_host(host):
        try:
            assert_public_hostname(host)
            return True
        except ValueError:
            return False
    @classmethod
    def _validate_url(cls,url):
        p=urlparse(url)
        if p.scheme not in {"http","https"} or not p.hostname: raise ValueError("Only public HTTP/HTTPS URLs are allowed.")
        if not cls._safe_host(p.hostname): raise ValueError("Local/private/reserved network targets are blocked.")
        return p
    def _robots_allowed(self,url):
        p=urlparse(url); robots_url=f"{p.scheme}://{p.netloc}/robots.txt"
        try:
            with pinned_client(timeout=httpx.Timeout(5.0,connect=2.0),follow_redirects=False,headers={"User-Agent":"My-AI"}) as client:
                response=client.get(robots_url)
                if 300 <= response.status_code < 400 and response.headers.get("location"):
                    target=str(httpx.URL(robots_url).join(response.headers["location"]))
                    self._validate_url(target)
                    response=client.get(target)
                # A 4xx robots response means the policy file is unavailable.
                # Do not convert that into a blanket site-wide deny.
                if 400 <= response.status_code < 500:
                    logger.warning("robots.txt unavailable", extra={"url": url, "status": response.status_code})
                    return True
                if response.status_code >= 500:
                    logger.warning("robots.txt server failure; failing closed", extra={"url": url, "status": response.status_code})
                    return False
                parser=robotparser.RobotFileParser()
                parser.parse(response.text.splitlines())
                return parser.can_fetch("My-AI",url)
        except Exception:
            return False

    def fetch(self,url,stop_event=None):
        self._validate_url(url)
        self._rate_limit(urlparse(url).hostname or "", stop_event)
        if not self._robots_allowed(url):
            raise ValueError("robots.txt disallows this URL or could not be verified.")
        timeout=httpx.Timeout(settings.learning_source_timeout_seconds, connect=min(3.0, settings.learning_source_timeout_seconds))
        with pinned_client(timeout=timeout,follow_redirects=False,headers={"User-Agent":"My-AI/0.2"}) as client:
            for _ in range(6):
                self._validate_url(url)
                r=client.get(url)
                if r.status_code in {429, 500, 502, 503, 504}:
                    delay = min(8.0, 2.0 ** _)
                    logger.warning("web fetch backoff", extra={"url": url, "status": r.status_code, "delay": delay})
                    if stop_event is not None:
                        if stop_event.wait(delay):
                            raise InterruptedError("learning stopped")
                    else:
                        time.sleep(delay)
                    continue
                if r.status_code not in {301,302,303,307,308}: break
                location=r.headers.get("location")
                if not location: break
                url=str(httpx.URL(url).join(location)); self._validate_url(url)
                self._rate_limit(urlparse(url).hostname or "", stop_event)
                if not self._robots_allowed(url): raise ValueError("robots.txt disallows redirect target.")
        r.raise_for_status()
        if "text/html" not in r.headers.get("content-type","") and "text/plain" not in r.headers.get("content-type",""): raise ValueError("URL does not contain HTML/text.")
        soup=BeautifulSoup(r.text,"html.parser")
        for n in soup(["script","style","noscript","svg","nav","footer"]): n.decompose()
        title=soup.title.get_text(" ",strip=True) if soup.title else url
        return title,re.sub(r"\s+"," ",soup.get_text(" ",strip=True))[:settings.max_web_chars]
