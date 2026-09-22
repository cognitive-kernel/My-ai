from __future__ import annotations
import re
from urllib.parse import urlparse, quote_plus
from urllib import robotparser
import httpx
from bs4 import BeautifulSoup
from .config import settings
from .network import assert_public_hostname, pinned_client
class WebLearner:
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
                if response.status_code == 404: return True
                if response.status_code >= 400: return False
                parser=robotparser.RobotFileParser()
                parser.parse(response.text.splitlines())
                return parser.can_fetch("My-AI",url)
        except Exception:
            return False

    def fetch(self,url):
        self._validate_url(url)
        if not self._robots_allowed(url):
            raise ValueError("robots.txt disallows this URL or could not be verified.")
        with pinned_client(timeout=20,follow_redirects=False,headers={"User-Agent":"My-AI/0.2"}) as client:
            for _ in range(6):
                self._validate_url(url)
                r=client.get(url)
                if r.status_code not in {301,302,303,307,308}: break
                location=r.headers.get("location")
                if not location: break
                url=str(httpx.URL(url).join(location)); self._validate_url(url)
                if not self._robots_allowed(url): raise ValueError("robots.txt disallows redirect target.")
        r.raise_for_status()
        if "text/html" not in r.headers.get("content-type","") and "text/plain" not in r.headers.get("content-type",""): raise ValueError("URL does not contain HTML/text.")
        soup=BeautifulSoup(r.text,"html.parser")
        for n in soup(["script","style","noscript","svg","nav","footer"]): n.decompose()
        title=soup.title.get_text(" ",strip=True) if soup.title else url
        return title,re.sub(r"\s+"," ",soup.get_text(" ",strip=True))[:settings.max_web_chars]
