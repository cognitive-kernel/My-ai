from __future__ import annotations
import ipaddress,re,socket
from urllib.parse import urlparse, quote_plus
import httpx
from bs4 import BeautifulSoup
from .config import settings
class WebLearner:
    def search(self,query,domains=None,limit=6):
        q=query+((" site:"+" OR site:".join(domains)) if domains else "")
        r=httpx.get("https://html.duckduckgo.com/html/?q="+quote_plus(q),timeout=20,follow_redirects=True,headers={"User-Agent":"My-AI/0.2"}); r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        return [{"title":a.get_text(" ",strip=True),"url":a.get("href")} for a in soup.select("a.result__a")[:limit] if a.get("href") and a.get_text(" ",strip=True)]
    @staticmethod
    def _safe_host(host):
        try:
            infos=socket.getaddrinfo(host,None,type=socket.SOCK_STREAM)
            return bool(infos) and all(ipaddress.ip_address(x[4][0]).is_global for x in infos)
        except (OSError,ValueError): return False
    @classmethod
    def _validate_url(cls,url):
        p=urlparse(url)
        if p.scheme not in {"http","https"} or not p.hostname: raise ValueError("Only public HTTP/HTTPS URLs are allowed.")
        if not cls._safe_host(p.hostname): raise ValueError("Local/private/reserved network targets are blocked.")
        return p
    def fetch(self,url):
        self._validate_url(url)
        for _ in range(6):
            r=httpx.get(url,timeout=20,follow_redirects=False,headers={"User-Agent":"My-AI/0.2"})
            if r.status_code not in {301,302,303,307,308}: break
            location=r.headers.get("location")
            if not location: break
            url=str(httpx.URL(url).join(location)); self._validate_url(url)
        r.raise_for_status()
        if "text/html" not in r.headers.get("content-type","") and "text/plain" not in r.headers.get("content-type",""): raise ValueError("URL does not contain HTML/text.")
        soup=BeautifulSoup(r.text,"html.parser")
        for n in soup(["script","style","noscript","svg","nav","footer"]): n.decompose()
        title=soup.title.get_text(" ",strip=True) if soup.title else url
        return title,re.sub(r"\s+"," ",soup.get_text(" ",strip=True))[:settings.max_web_chars]
