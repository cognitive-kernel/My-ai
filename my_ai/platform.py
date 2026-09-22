from __future__ import annotations

import json
import math
import os
import shutil
import urllib.parse
import urllib.robotparser
from pathlib import Path
from typing import Any

import httpx

from .config import settings
from .db import connect, fetch_all
from functools import lru_cache
import time


def ollama_embed(text: str, model: str | None = None) -> list[float]:
    model = model or settings.embedding_model
    response = httpx.post(
        f"{settings.ollama_base_url.rstrip('/')}/api/embed",
        json={"model": model, "input": text},
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    embeddings = data.get("embeddings") or []
    if not embeddings:
        raise RuntimeError("Ollama returned no embedding.")
    return [float(x) for x in embeddings[0]]


def ollama_embed_batch(texts: list[str], model: str | None = None) -> list[list[float]]:
    if not texts:
        return []
    model = model or settings.embedding_model
    response = httpx.post(
        f"{settings.ollama_base_url.rstrip('/')}/api/embed",
        json={"model": model, "input": texts},
        timeout=120,
    )
    response.raise_for_status()
    embeddings = response.json().get("embeddings") or []
    if len(embeddings) != len(texts):
        raise RuntimeError("Ollama returned an unexpected embedding count.")
    return [[float(x) for x in item] for item in embeddings]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


@lru_cache(maxsize=128)
def _hybrid_search_cached(query: str, limit: int, bucket: int) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 50))
    from .db import _normalize_search_text
    normalized = _normalize_search_text(query)
    tokens = [t for t in normalized.replace('"', ' ').split() if t][:12]
    match = " ".join(f'"{t}"' for t in tokens) if tokens else '""'
    lexical = fetch_all(
        """SELECT k.id, bm25(knowledge_fts) AS fts_rank
           FROM knowledge_fts JOIN knowledge k ON k.id=knowledge_fts.rowid
           WHERE knowledge_fts MATCH ? ORDER BY fts_rank""",
        (match,),
    ) if tokens else []
    lexical_scores = {}
    if lexical:
        ranks = [float(r["fts_rank"]) for r in lexical]
        best, worst = min(ranks), max(ranks)
        span = worst - best
        lexical_scores = {int(r["id"]):(1.0 if span == 0 else (worst-float(r["fts_rank"]))/span) for r in lexical}
    rows = fetch_all("SELECT * FROM knowledge ORDER BY id DESC")
    cached = fetch_all("SELECT knowledge_id,content_hash,embedding FROM knowledge_embeddings WHERE model=?", (settings.embedding_model,))
    cache = {int(r["knowledge_id"]): r for r in cached}
    missing = []
    missing_rows = []
    for row in rows:
        cached_row = cache.get(int(row["id"]))
        if not cached_row or cached_row["content_hash"] != (row.get("content_hash") or ""):
            missing_rows.append(row)
            missing.append(f'{row.get("title","")}\n{row.get("content","")}\n{row.get("topic","")}')
    if missing:
        try:
            vectors = ollama_embed_batch(missing)
            from .db import connect
            with connect() as conn:
                for row, vector in zip(missing_rows, vectors):
                    conn.execute(
                        "INSERT INTO knowledge_embeddings(knowledge_id,content_hash,model,embedding) VALUES(?,?,?,?) "
                        "ON CONFLICT(knowledge_id,model) DO UPDATE SET content_hash=excluded.content_hash,embedding=excluded.embedding,created_at=CURRENT_TIMESTAMP",
                        (row["id"], row.get("content_hash") or "", settings.embedding_model, json.dumps(vector, separators=(",",":"))),
                    )
                conn.commit()
            for row, vector in zip(missing_rows, vectors):
                cache[int(row["id"])] = {"content_hash": row.get("content_hash") or "", "embedding": json.dumps(vector)}
        except Exception:
            pass
    try:
        qvec = ollama_embed(normalized)
    except Exception:
        qvec = []
    for row in rows:
        semantic = 0.0
        cached_row = cache.get(int(row["id"]))
        if qvec and cached_row:
            try:
                semantic = max(0.0, min(1.0, cosine_similarity(qvec, json.loads(cached_row["embedding"]))))
            except Exception:
                semantic = 0.0
        lexical_score = lexical_scores.get(int(row["id"]), 0.0)
        row["semantic_score"] = round(semantic, 6)
        row["lexical_score"] = round(lexical_score, 6)
        row["hybrid_score"] = round(0.65*semantic + 0.35*lexical_score, 6)
        row["relevance"] = row["hybrid_score"]
        row["confidence"] = None
    return sorted(rows, key=lambda x:x["hybrid_score"], reverse=True)[:limit]


def hybrid_search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    limit=max(1,min(limit,50))
    bucket=int(time.monotonic() // max(1,settings.cache_ttl_seconds))
    return _hybrid_search_cached(query.strip(),limit,bucket)


def model_health() -> dict[str, Any]:
    models = []
    try:
        r = httpx.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags", timeout=10)
        r.raise_for_status()
        models = [m.get("name") for m in r.json().get("models", [])]
    except Exception as exc:
        return {"healthy": False, "provider": "ollama", "error": str(exc), "models": models}
    return {
        "healthy": settings.ollama_model in models,
        "provider": "ollama",
        "routing_model": os.getenv("ROUTER_MODEL", settings.ollama_model),
        "coding_model": os.getenv("CODING_MODEL", settings.ollama_model),
        "fallback_model": os.getenv("FALLBACK_MODEL", settings.ollama_model),
        "models": models,
    }


def choose_model(task: str) -> str:
    low = task.lower()
    coding = any(x in low for x in ("code", "python", "sql", "debug", "کد", "برنامه", "sql server"))
    return os.getenv("CODING_MODEL", settings.ollama_model) if coding else os.getenv("ROUTER_MODEL", settings.ollama_model)


def backup_database(destination: str) -> str:
    src = Path(settings.db_path)
    dst = Path(destination).expanduser().resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise FileNotFoundError(src)
    with connect() as conn, sqlite3_backup(conn, dst) as _:
        pass
    return str(dst)


class sqlite3_backup:
    def __init__(self, source, destination: Path):
        import sqlite3
        self.source = source
        self.destination = destination
        self.destination_conn = sqlite3.connect(destination)

    def __enter__(self):
        self.source.backup(self.destination_conn)
        self.destination_conn.commit()
        return self

    def __exit__(self, *_):
        self.destination_conn.close()


def export_database(destination: str) -> str:
    dst = Path(destination).expanduser().resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        data = {}
        for table in ("users","tool_permissions","knowledge","chat_sessions","conversations","learning_sessions","agent_runs","generated_projects","security_scans","audit_log"):
            try:
                data[table] = [dict(x) for x in conn.execute(f"SELECT * FROM {table}").fetchall()]
            except Exception:
                data[table] = []
    dst.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(dst)


def import_database(source: str) -> dict[str, Any]:
    path = Path(source).expanduser().resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    allowed = {"knowledge","chat_sessions","conversations","learning_sessions","agent_runs","generated_projects","security_scans"}
    inserted = {}
    with connect() as conn:
        for table in allowed:
            rows = data.get(table) or []
            if not rows:
                continue
            columns = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            for row in rows:
                cols = [c for c in columns if c in row and c != "id"]
                if not cols:
                    continue
                marks = ",".join("?" for _ in cols)
                conn.execute(f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({marks})", tuple(row[c] for c in cols))
            inserted[table] = len(rows)
        conn.commit()
    return inserted


def _assert_public_http_url(url: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL must use http:// or https:// and include a hostname.")
    import ipaddress
    import socket
    try:
        addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(parsed.hostname, None, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError("Hostname could not be resolved.") from exc
    if not addresses or not all(ip.is_global and not ip.is_multicast for ip in addresses):
        raise ValueError("Target must resolve only to globally routable addresses.")
    return parsed


def web_fetch_policy(url: str) -> dict[str, Any]:
    parsed = _assert_public_http_url(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        with httpx.Client(timeout=httpx.Timeout(5.0, connect=2.0), follow_redirects=False) as client:
            response = client.get(robots_url, headers={"User-Agent": "My-AI"})
            if 300 <= response.status_code < 400 and response.headers.get("location"):
                redirect = urllib.parse.urljoin(robots_url, response.headers["location"])
                _assert_public_http_url(redirect)
                response = client.get(redirect, headers={"User-Agent": "My-AI"})
            if response.status_code >= 400:
                return {"url": url, "robots_url": robots_url, "allowed": False, "reason": f"robots HTTP {response.status_code}"}
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(robots_url)
            parser.parse(response.text.splitlines())
            return {"url": url, "robots_url": robots_url, "allowed": parser.can_fetch("My-AI", url)}
    except Exception as exc:
        return {"url": url, "robots_url": robots_url, "allowed": False, "reason": str(exc)}


def resource_status() -> dict[str, Any]:
    try:
        import psutil
        return {"cpu_percent": psutil.cpu_percent(interval=0.1), "ram_percent": psutil.virtual_memory().percent}
    except Exception:
        return {"cpu_percent": None, "ram_percent": None, "psutil_installed": False}


def voice_status() -> dict[str, Any]:
    return {
        "whisper_cpp": shutil.which("whisper-cli") or shutil.which("main"),
        "piper": shutil.which("piper"),
        "offline": bool((shutil.which("whisper-cli") or shutil.which("main")) and shutil.which("piper")),
    }


def eval_retrieval() -> dict[str, Any]:
    cases = [
        ("Python list tuple", "Python"),
        ("SQL Server index execution plan", "SQL Server"),
        ("امنیت پن‌تست", "Pentest"),
    ]
    results = []
    for query, expected in cases:
        try:
            hits = hybrid_search(query, 3)
            results.append({"query": query, "expected": expected, "hit": bool(hits), "top": hits[0]["title"] if hits else None})
        except Exception as exc:
            results.append({"query": query, "expected": expected, "hit": False, "error": str(exc)})
    return {"cases": results, "passed": sum(1 for x in results if x["hit"]), "total": len(results)}


