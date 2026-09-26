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
from .network import assert_public_hostname, pinned_client
from .backup_crypto import encrypt_file, decrypt_file
from functools import lru_cache
import time

BACKUP_FORMAT_VERSION = 1


def _ollama_url(path: str) -> str:
    base = settings.ollama_base_url.rstrip("/")
    if settings.offline_strict:
        host = urllib.parse.urlparse(base).hostname
        import ipaddress
        try:
            if not host or not ipaddress.ip_address(host).is_loopback:
                raise ValueError
        except ValueError as exc:
            raise RuntimeError("Offline strict mode permits only loopback Ollama endpoints.") from exc
    return base + path

def ollama_embed(text: str, model: str | None = None) -> list[float]:
    model = model or settings.embedding_model
    response = httpx.post(
        _ollama_url("/api/embed"),
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
        _ollama_url("/api/embed"),
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
    calibration: dict[float, list[int]] = {}
    for item in fetch_all("SELECT score,relevant FROM retrieval_judgments"):
        score_bucket=round(float(item["score"] or 0.0),1)
        state=calibration.setdefault(score_bucket,[0,0])
        state[0]+=1
        state[1]+=int(item["relevant"] or 0)
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
        score_bucket=round(float(row["hybrid_score"]),1)
        samples=calibration.get(bucket, (0,0))
        if samples[0] >= 5:
            row["confidence"]=round((samples[1]+1)/(samples[0]+2),6)
            row["confidence_basis"]="empirical score-bucket calibration with Laplace smoothing"
            row["confidence_calibrated"]=True
            row["confidence_samples"]=samples[0]
        else:
            row["confidence"]=None
            row["confidence_basis"]="uncalibrated; fewer than 5 judgments in score bucket"
            row["confidence_calibrated"]=False
            row["confidence_samples"]=samples[0]
    return sorted(rows, key=lambda x:x["hybrid_score"], reverse=True)[:limit]


def invalidate_hybrid_search_cache() -> None:
    _hybrid_search_cached.cache_clear()


def hybrid_search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    limit=max(1,min(limit,50))
    bucket=int(time.monotonic() // max(1,settings.cache_ttl_seconds))
    return _hybrid_search_cached(query.strip(),limit,bucket)


def model_health() -> dict[str, Any]:
    models = []
    try:
        r = httpx.get(_ollama_url("/api/tags"), timeout=10)
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


DATA_ROOT = Path(settings.db_path).expanduser().resolve().parent
BACKUP_ROOT = Path(os.getenv("MYAI_BACKUP_ROOT", str(DATA_ROOT / "backups"))).expanduser().resolve()


def _safe_backup_path(value: str) -> Path:
    path=Path(value).expanduser().resolve()
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        path.relative_to(BACKUP_ROOT)
    except ValueError as exc:
        raise ValueError(f"Backup paths must stay under {BACKUP_ROOT}.") from exc
    return path


def backup_database(destination: str, password: str | None = None) -> str:
    src = Path(settings.db_path)
    dst = _safe_backup_path(destination)
    if password:
        temp = dst.with_name(dst.name + ".plain.tmp")
        temp.parent.mkdir(parents=True, exist_ok=True)
        with connect() as conn, sqlite3_backup(conn, temp) as _:
            pass
        try:
            return encrypt_file(temp, dst, password)
        finally:
            temp.unlink(missing_ok=True)
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


def export_database(destination: str, password: str | None = None) -> str:
    dst = _safe_backup_path(destination)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        data = {}
        for table in ("users","tool_permissions","knowledge","chat_sessions","conversations","learning_sessions","agent_runs","generated_projects","security_scans","audit_log"):
            try:
                data[table] = [dict(x) for x in conn.execute(f"SELECT * FROM {table}").fetchall()]
            except Exception:
                data[table] = []
    payload = {"metadata": {"format_version": BACKUP_FORMAT_VERSION, "app_version": "0.2.0"}, "tables": data}
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    if password:
        from .backup_crypto import encrypt_bytes
        dst.write_bytes(encrypt_bytes(raw, password))
    else:
        dst.write_bytes(raw)
    return str(dst)


def _import_data(data: dict[str, Any]) -> dict[str, Any]:
    if "tables" in data:
        metadata = data.get("metadata") or {}
        version = int(metadata.get("format_version", 0))
        if version > BACKUP_FORMAT_VERSION:
            raise ValueError(f"Backup format {version} is newer than supported format {BACKUP_FORMAT_VERSION}.")
        data = data["tables"]
    allowed = {"knowledge","chat_sessions","conversations","learning_sessions","agent_runs","generated_projects","security_scans"}
    inserted = {}
    with connect() as conn:
        for table in allowed:
            rows = data.get(table) or []
            if not rows:
                continue
            columns = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
            for row in rows:
                cols = [col for col in columns if col in row and col != "id"]
                if not cols:
                    continue
                marks = ",".join("?" for _ in cols)
                conn.execute(f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({marks})", tuple(row[col] for col in cols))
            inserted[table] = len(rows)
        conn.commit()
    return inserted


def import_database(source: str) -> dict[str, Any]:
    path = _safe_backup_path(source)
    return _import_data(json.loads(path.read_text(encoding="utf-8")))


def import_encrypted_database(source: str, password: str) -> dict[str, Any]:
    from .backup_crypto import decrypt_bytes
    data = json.loads(decrypt_bytes(_safe_backup_path(source).read_bytes(), password).decode("utf-8"))
    return _import_data(data)


def restore_encrypted_backup(source: str, destination: str, password: str) -> str:
    return decrypt_file(_safe_backup_path(source), _safe_backup_path(destination), password)


def _assert_public_http_url(url: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL must use http:// or https:// and include a hostname.")
    assert_public_hostname(parsed.hostname)
    return parsed


def web_fetch_policy(url: str) -> dict[str, Any]:
    if settings.offline_strict:
        return {"url": url, "allowed": False, "reason": "offline strict mode enabled"}
    parsed = _assert_public_http_url(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    try:
        with pinned_client(timeout=httpx.Timeout(5.0, connect=2.0), follow_redirects=False) as client:
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
        "whisper_cpp": os.getenv("WHISPER_CPP_BIN") or shutil.which("whisper-cli"),
        "piper": shutil.which("piper"),
        "offline": bool((os.getenv("WHISPER_CPP_BIN") or shutil.which("whisper-cli")) and shutil.which("piper")),
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


