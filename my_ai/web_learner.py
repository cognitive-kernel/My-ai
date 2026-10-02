from __future__ import annotations
import re
import time
import threading
import logging
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
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
    _host_failures: dict[str, int] = {}
    _host_last_failure: dict[str, float] = {}
    _host_semaphores: dict[str, threading.BoundedSemaphore] = {}
    _min_interval = 1.0
    _max_concurrency_per_host = 2
    _max_retries = 5
    _max_backoff = 30.0
    _failure_threshold = 10
    _failure_cooldown = 30.0

    @classmethod
    def _host_semaphore(cls, host: str) -> threading.BoundedSemaphore:
        with cls._rate_lock:
            semaphore = cls._host_semaphores.get(host)
            if semaphore is None:
                semaphore = threading.BoundedSemaphore(cls._max_concurrency_per_host)
                cls._host_semaphores[host] = semaphore
            return semaphore

    @classmethod
    def _rate_limit(cls, host: str, stop_event=None) -> None:
        now = time.monotonic()
        with cls._rate_lock:
            previous = cls._last_fetch.get(host, 0.0)
            wait = cls._min_interval - (now - previous)
            failures = cls._host_failures.get(host, 0)
            last_failure = cls._host_last_failure.get(host, 0.0)
            if failures >= cls._failure_threshold and now - last_failure < cls._failure_cooldown:
                raise RuntimeError(f"Host temporarily blocked after repeated fetch failures: {host}")
        if wait > 0:
            logger.info("web fetch rate limit wait", extra={"host": host, "wait": round(wait, 3)})
            if stop_event is not None:
                if stop_event.wait(wait):
                    raise InterruptedError("learning stopped")
            else:
                time.sleep(wait)
            now = time.monotonic()
        with cls._rate_lock:
            cls._last_fetch[host] = now

    @classmethod
    def _record_failure(cls, host: str) -> None:
        with cls._rate_lock:
            cls._host_failures[host] = cls._host_failures.get(host, 0) + 1
            cls._host_last_failure[host] = time.monotonic()

    @classmethod
    def _record_success(cls, host: str) -> None:
        with cls._rate_lock:
            cls._host_failures.pop(host, None)
            cls._host_last_failure.pop(host, None)

    @classmethod
    def _retry_delay(cls, attempt: int, response: httpx.Response | None = None) -> float:
        retry_after = response.headers.get("Retry-After") if response is not None else None
        if retry_after:
            try:
                return min(cls._max_backoff, max(0.0, float(retry_after)))
            except ValueError:
                try:
                    target = parsedate_to_datetime(retry_after)
                    if target.tzinfo is None:
                        target = target.replace(tzinfo=timezone.utc)
                    return min(cls._max_backoff, max(0.0, target.timestamp() - datetime.now(timezone.utc).timestamp()))
                except (TypeError, ValueError, OverflowError) as exc:
                    logger.debug("invalid Retry-After header: %s", exc)
        base = min(cls._max_backoff, 2.0 ** attempt)
        return min(cls._max_backoff, base * random.uniform(0.5, 1.0))

    def search(self,query,domains=None,limit=6):
        provider = str(getattr(settings, "research_search_provider", "duckduckgo-html") or "duckduckgo-html")
        if provider != "duckduckgo-html": raise ValueError(f"Unsupported research search provider: {provider}")
        configured_allow = [x.strip().lower() for x in str(getattr(settings, "research_domain_allowlist", "") or "").split(",") if x.strip()]
        configured_deny = [x.strip().lower() for x in str(getattr(settings, "research_domain_denylist", "") or "").split(",") if x.strip()]
        requested = [str(x).strip().lower() for x in (domains or []) if str(x).strip()]
        allowed = requested or configured_allow
        q=query+((" site:"+" OR site:".join(allowed)) if allowed else "")
        timeout=float(getattr(settings, "research_source_timeout", 15) or 15)
        r=httpx.get("https://html.duckduckgo.com/html/?q="+quote_plus(q),timeout=timeout,follow_redirects=True,headers={"User-Agent":"My-AI/0.2"}); r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        results=[]
        for a in soup.select("a.result__a"):
            url=a.get("href"); title=a.get_text(" ",strip=True); host=(urlparse(url).hostname or "").lower() if url else ""
            if not url or not title: continue
            if configured_deny and any(host == d or host.endswith("."+d) for d in configured_deny): continue
            if allowed and not any(host == d or host.endswith("."+d) for d in allowed): continue
            results.append({"title":title,"url":url})
            if len(results)>=limit: break
        return results
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
                    logger.debug("robots.txt unavailable", extra={"url": url, "status": response.status_code})
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
        host = (urlparse(url).hostname or "").lower()
        self._rate_limit(host, stop_event)
        if not self._robots_allowed(url):
            self._record_failure(host)
            raise ValueError("robots.txt disallows this URL or could not be verified.")
        timeout=httpx.Timeout(float(getattr(settings, "research_source_timeout", settings.learning_source_timeout_seconds)), connect=min(3.0, float(getattr(settings, "research_source_timeout", settings.learning_source_timeout_seconds))))
        semaphore = self._host_semaphore(host)
        acquired = semaphore.acquire(timeout=settings.learning_source_timeout_seconds)
        if not acquired:
            raise TimeoutError(f"Timed out waiting for host concurrency slot: {host}")
        try:
            with pinned_client(timeout=timeout,follow_redirects=False,headers={"User-Agent":"My-AI/0.2"}) as client:
                last_error = None
                for attempt in range(self._max_retries + 1):
                    self._validate_url(url)
                    current_host = (urlparse(url).hostname or "").lower()
                    self._rate_limit(current_host, stop_event)
                    try:
                        r=client.get(url)
                    except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
                        last_error = exc
                        self._record_failure(current_host)
                        if attempt >= self._max_retries:
                            raise
                        delay = self._retry_delay(attempt)
                        logger.warning("web fetch retry after transport failure", extra={"url": url, "attempt": attempt + 1, "delay": round(delay, 3), "error": type(exc).__name__})
                        if stop_event is not None:
                            if stop_event.wait(delay): raise InterruptedError("learning stopped")
                        else: time.sleep(delay)
                        continue
                    if r.status_code in {429, 500, 502, 503, 504}:
                        self._record_failure(current_host)
                        if attempt >= self._max_retries:
                            r.raise_for_status()
                        delay = self._retry_delay(attempt, r)
                        logger.warning("web fetch backoff", extra={"url": url, "status": r.status_code, "attempt": attempt + 1, "delay": round(delay, 3)})
                        if stop_event is not None:
                            if stop_event.wait(delay): raise InterruptedError("learning stopped")
                        else: time.sleep(delay)
                        continue
                    if r.status_code not in {301,302,303,307,308}:
                        if r.status_code >= 400:
                            self._record_failure(current_host)
                        else:
                            self._record_success(current_host)
                        break
                    location=r.headers.get("location")
                    if not location:
                        self._record_failure(current_host)
                        break
                    url=str(httpx.URL(url).join(location)); self._validate_url(url)
                    redirect_host = (urlparse(url).hostname or "").lower()
                    self._rate_limit(redirect_host, stop_event)
                    if not self._robots_allowed(url):
                        self._record_failure(redirect_host)
                        raise ValueError("robots.txt disallows redirect target.")
                else:
                    raise RuntimeError(f"Web fetch retry budget exhausted: {url}") from last_error
            r.raise_for_status()
            if "text/html" not in r.headers.get("content-type","") and "text/plain" not in r.headers.get("content-type",""): raise ValueError("URL does not contain HTML/text.")
            soup=BeautifulSoup(r.text,"html.parser")
            for n in soup(["script","style","noscript","svg","nav","footer"]): n.decompose()
            title=soup.title.get_text(" ",strip=True) if soup.title else url
            return title,re.sub(r"\s+"," ",soup.get_text(" ",strip=True))[:int(getattr(settings, "max_web_chars", settings.max_web_chars))]
        finally:
            semaphore.release()
