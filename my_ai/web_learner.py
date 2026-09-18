from __future__ import annotations
import ipaddress,re,socket
from urllib.parse import urlparse, quote_plus
import httpx
from bs4 import BeautifulSoup
from .config import settings
class WebLearner:
    def search(self, query, domains=None, limit=6):
        q = query + ((" site:" + " OR site:".join(domains)) if domains else "")
        url = "https://html.duckduckgo.com/html/?q=" + quote_plus(q)
        r = httpx.get(url, timeout=20, follow_redirects=True, headers={"User-Agent":"My-AI/0.2"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for a in soup.select("a.result__a")[:limit]:
            href = a.get("href")
            title = a.get_text(" ", strip=True)
            if href and title: results.append({"title": title, "url": href})
        return results
    @staticmethod
    def _safe_host(host):
        try:
            for info in socket.getaddrinfo(host,None):
                ip=ipaddress.ip_address(info[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved: return False
            return True
        except (OSError,ValueError): return False
    def fetch(self,url):
        p=urlparse(url)
        if p.scheme not in {"http","https"} or not p.hostname: raise ValueError("Only HTTP/HTTPS URLs are allowed.")
        if not self._safe_host(p.hostname): raise ValueError("Local/private network targets are blocked.")
        r=httpx.get(url,timeout=20,follow_redirects=True,headers={"User-Agent":"My-AI/0.2"})
        r.raise_for_status()
        if "text/html" not in r.headers.get("content-type","") and "text/plain" not in r.headers.get("content-type",""): raise ValueError("URL does not contain HTML/text.")
        soup=BeautifulSoup(r.text,"html.parser")
        for n in soup(["script","style","noscript","svg","nav","footer"]): n.decompose()
        title=soup.title.get_text(" ",strip=True) if soup.title else url
        return title,re.sub(r"\s+"," ",soup.get_text(" ",strip=True))[:settings.max_web_chars]
