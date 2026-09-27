from __future__ import annotations

import json
import hashlib
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
from .access_policy import assert_mutation_allowed
from functools import lru_cache
import time

BACKUP_FORMAT_VERSION = 3


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
def _hybrid_search_cached(query: str, limit: int, bucket: int, verified_only: bool) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 50))
    from .db import _normalize_search_text

    normalized = _normalize_search_text(query)
    tokens = [t for t in normalized.replace('"', ' ').split() if t][:12]
    match = " ".join(f'"{t}"' for t in tokens) if tokens else '""'
    verification_clause = " AND k.verification_status IN ('verified','approved')" if verified_only else ""

    lexical = fetch_all(
        f"""SELECT k.id, bm25(knowledge_fts) AS fts_rank
            FROM knowledge_fts JOIN knowledge k ON k.id=knowledge_fts.rowid
            WHERE knowledge_fts MATCH ?{verification_clause}
            ORDER BY fts_rank""",
        (match,),
    ) if tokens else []
    lexical_scores: dict[int, float] = {}
    if lexical:
        ranks = [float(row["fts_rank"]) for row in lexical]
        best, worst = min(ranks), max(ranks)
        span = worst - best
        lexical_scores = {
            int(row["id"]): 1.0 if span == 0 else max(0.0, min(1.0, (worst - float(row["fts_rank"])) / span))
            for row in lexical
        }

    rows = fetch_all(
        "SELECT * FROM knowledge WHERE verification_status IN ('verified','approved') ORDER BY id DESC"
        if verified_only
        else "SELECT * FROM knowledge ORDER BY id DESC"
    )
    cached = fetch_all(
        "SELECT knowledge_id,content_hash,embedding FROM knowledge_embeddings WHERE model=?",
        (settings.embedding_model,),
    )
    cache = {int(row["knowledge_id"]): row for row in cached}

    missing_rows: list[dict[str, Any]] = []
    missing_texts: list[str] = []
    for row in rows:
        cached_row = cache.get(int(row["id"]))
        if not cached_row or cached_row["content_hash"] != (row.get("content_hash") or ""):
            missing_rows.append(row)
            missing_texts.append(f'{row.get("title","")}\n{row.get("content","")}\n{row.get("topic","")}')

    embedding_error: str | None = None
    if missing_rows and not settings.read_only:
        try:
            vectors = ollama_embed_batch(missing_texts, settings.embedding_model)
            with connect() as conn:
                for row, vector in zip(missing_rows, vectors):
                    conn.execute(
                        "INSERT INTO knowledge_embeddings(knowledge_id,content_hash,model,embedding) VALUES(?,?,?,?) "
                        "ON CONFLICT(knowledge_id,model) DO UPDATE SET content_hash=excluded.content_hash,embedding=excluded.embedding,created_at=CURRENT_TIMESTAMP",
                        (
                            row["id"],
                            row.get("content_hash") or "",
                            settings.embedding_model,
                            json.dumps(vector, separators=(",", ":")),
                        ),
                    )
                conn.commit()
            for row, vector in zip(missing_rows, vectors):
                cache[int(row["id"])] = {
                    "content_hash": row.get("content_hash") or "",
                    "embedding": json.dumps(vector, separators=(",", ":")),
                }
        except Exception as exc:
            embedding_error = str(exc)

    qvec: list[float] = []
    try:
        if rows:
            qvec = ollama_embed(normalized, settings.embedding_model)
    except Exception as exc:
        embedding_error = embedding_error or str(exc)

    calibration: dict[float, tuple[int, int]] = {}
    for judgment in fetch_all("SELECT score,relevant FROM retrieval_judgments"):
        score = max(0.0, min(1.0, float(judgment["score"] or 0.0)))
        score_bucket = float(f"{score:.1f}")
        count: int
        relevant_count: int
        count, relevant_count = calibration.get(score_bucket, (0, 0))
        calibration[score_bucket] = (count + 1, relevant_count + int(bool(judgment["relevant"])))

    for row in rows:
        semantic = 0.0
        cached_row = cache.get(int(row["id"]))
        if qvec and cached_row:
            try:
                semantic = max(0.0, min(1.0, cosine_similarity(qvec, json.loads(cached_row["embedding"]))))
            except (TypeError, ValueError, json.JSONDecodeError):
                semantic = 0.0

        lexical_score = lexical_scores.get(int(row["id"]), 0.0)
        hybrid_score = 0.65 * semantic + 0.35 * lexical_score if qvec else lexical_score
        row["semantic_score"] = round(semantic, 6)
        row["lexical_score"] = round(lexical_score, 6)
        row["hybrid_score"] = round(hybrid_score, 6)
        row["relevance"] = row["hybrid_score"]

        citation_id = f"K{int(row['id'])}"
        source_url = str(row.get("source_url") or "").strip() or f"local://knowledge/{int(row['id'])}"
        row["provenance"] = {
            "citation_id": citation_id,
            "source_url": source_url,
            "title": str(row.get("title") or ""),
            "content_hash": row.get("content_hash"),
            "verification_status": row.get("verification_status"),
            "retrieval": {
                "semantic_score": row["semantic_score"],
                "lexical_score": row["lexical_score"],
                "hybrid_score": row["hybrid_score"],
            },
        }
        row["citation_required"] = True

        score_bucket = round(float(row["hybrid_score"]), 1)
        samples, relevant = calibration.get(score_bucket, (0, 0))
        if samples >= 5:
            row["confidence"] = round((relevant + 1) / (samples + 2), 6)
            row["confidence_basis"] = "empirical retrieval-judgment calibration with Laplace smoothing"
            row["confidence_calibrated"] = True
            row["confidence_samples"] = samples
        else:
            row["confidence"] = None
            row["confidence_basis"] = "uncalibrated; fewer than 5 retrieval judgments in this score bucket"
            row["confidence_calibrated"] = False
            row["confidence_samples"] = samples

        row["embedding_model"] = settings.embedding_model
        row["semantic_available"] = bool(qvec)
        row["hybrid_mode"] = "semantic+fts5" if qvec else "fts5-only"
        if embedding_error:
            row["embedding_error"] = embedding_error[:500]

    return sorted(rows, key=lambda item: item["hybrid_score"], reverse=True)[:limit]

def invalidate_hybrid_search_cache() -> None:
    _hybrid_search_cached.cache_clear()


def hybrid_search(query: str, limit: int = 8, verified_only: bool = False) -> list[dict[str, Any]]:
    limit=max(1,min(limit,50))
    bucket=int(time.monotonic() // max(1,settings.cache_ttl_seconds))
    return _hybrid_search_cached(query.strip(),limit,bucket,bool(verified_only))


def model_health() -> dict[str, Any]:
    configured = {
        "default": settings.ollama_model,
        "routing": settings.routing_model,
        "coding": settings.coding_model,
        "fallback": settings.fallback_model,
        "embedding": settings.embedding_model,
    }
    try:
        r = httpx.get(_ollama_url("/api/tags"), timeout=10)
        r.raise_for_status()
        available = {str(m.get("name")) for m in r.json().get("models", []) if m.get("name")}
        models = {}
        for role, name in configured.items():
            models[role] = {"name": name, "available": name in available}
        healthy = bool(models["default"]["available"] and models["fallback"]["available"])
        return {
            "healthy": healthy,
            "provider": "ollama",
            "models": models,
            "available": sorted(available),
            "fallback_ready": models["fallback"]["available"],
        }
    except Exception as exc:
        return {
            "healthy": False,
            "provider": "ollama",
            "models": {role: {"name": name, "available": False} for role, name in configured.items()},
            "available": [],
            "fallback_ready": False,
            "error": str(exc),
        }


def choose_model(task: str) -> str:
    low = task.lower()
    coding = any(x in low for x in ("code", "python", "sql", "debug", "کد", "برنامه", "sql server"))
    return os.getenv("CODING_MODEL", settings.ollama_model) if coding else os.getenv("ROUTER_MODEL", settings.ollama_model)


DATA_ROOT = Path(settings.db_path).expanduser().resolve().parent
BACKUP_ROOT = Path(os.getenv("MYAI_BACKUP_ROOT", str(DATA_ROOT / "backups"))).expanduser().resolve()


def _safe_backup_path(value: str, *, create_parent: bool = True) -> Path:
    path = Path(value).expanduser().resolve()
    try:
        path.relative_to(BACKUP_ROOT)
    except ValueError as exc:
        raise ValueError(f"Backup paths must stay under {BACKUP_ROOT}.") from exc
    if create_parent:
        BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    return path


def _atomic_replace_bytes(destination: Path, payload: bytes) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_name(f".{destination.name}.tmp-{os.getpid()}-{time.time_ns()}")
    try:
        with tmp.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, destination)
        return str(destination)
    finally:
        tmp.unlink(missing_ok=True)


def _atomic_sqlite_backup(destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_name(f".{destination.name}.tmp-{os.getpid()}-{time.time_ns()}")
    try:
        with connect() as conn, sqlite3_backup(conn, tmp) as _:
            pass
        os.replace(tmp, destination)
        return str(destination)
    finally:
        tmp.unlink(missing_ok=True)


def _backup_manifest(tables: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    canonical = json.dumps(tables, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "format_version": BACKUP_FORMAT_VERSION,
        "app_version": "0.2.0",
        "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "tables": sorted(tables),
    }


def _verify_export_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("tables"), dict):
        raise ValueError("Backup payload is invalid.")
    metadata = payload.get("metadata") or {}
    version = int(metadata.get("format_version", 0))
    if version < 2 or version > BACKUP_FORMAT_VERSION:
        raise ValueError(f"Unsupported backup format {version}.")
    canonical = json.dumps(payload["tables"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected = str(metadata.get("sha256") or "")
    actual = hashlib.sha256(canonical).hexdigest()
    if not expected or expected != actual:
        raise ValueError("Backup integrity check failed: SHA-256 mismatch.")
    return metadata


def backup_database(destination: str, password: str | None = None) -> str:
    assert_mutation_allowed("database backup")
    src = Path(settings.db_path)
    dst = _safe_backup_path(destination)
    if not src.exists():
        raise FileNotFoundError(src)
    if password:
        plain = dst.with_name(f".{dst.name}.plain-{os.getpid()}-{time.time_ns()}")
        encrypted = dst.with_name(f".{dst.name}.encrypted-{os.getpid()}-{time.time_ns()}")
        try:
            _atomic_sqlite_backup(plain)
            encrypt_file(plain, encrypted, password)
            os.replace(encrypted, dst)
            return str(dst)
        finally:
            plain.unlink(missing_ok=True)
            encrypted.unlink(missing_ok=True)
    return _atomic_sqlite_backup(dst)


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
    assert_mutation_allowed("database export")
    dst = _safe_backup_path(destination)
    data = {}
    with connect() as conn:
        for table in ("users","tool_permissions","knowledge","chat_sessions","conversations","learning_sessions","agent_runs","generated_projects","security_scans","audit_log","retrieval_judgments","knowledge_audit"):
            try:
                data[table] = [dict(x) for x in conn.execute(f"SELECT * FROM {table}").fetchall()]
            except Exception:
                data[table] = []
    metadata = _backup_manifest(data)
    payload = {"metadata": metadata, "tables": data}
    raw = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    if password:
        from .backup_crypto import encrypt_bytes
        raw = encrypt_bytes(raw, password)
    return _atomic_replace_bytes(dst, raw)


def _import_data(data: dict[str, Any]) -> dict[str, Any]:
    assert_mutation_allowed("database import")
    if "tables" in data:
        _verify_export_payload(data)
        data = data["tables"]
    allowed = {"knowledge","chat_sessions","conversations","learning_sessions","agent_runs","generated_projects","security_scans"}
    inserted = {}
    with connect() as conn:
        try:
            for table in allowed:
                rows = data.get(table) or []
                if not rows:
                    continue
                columns = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
                inserted_count = 0
                for row in rows:
                    cols = [col for col in columns if col in row]
                    if not cols:
                        continue
                    marks = ",".join("?" for _ in cols)
                    cursor = conn.execute(
                        f"INSERT OR IGNORE INTO {table} ({','.join(cols)}) VALUES ({marks})",
                        tuple(row[col] for col in cols),
                    )
                    inserted_count += max(cursor.rowcount, 0)
                if inserted_count:
                    inserted[table] = inserted_count
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return inserted


def import_database(source: str) -> dict[str, Any]:
    path = _safe_backup_path(source, create_parent=False)
    raw = path.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Backup is not a valid unencrypted JSON export.") from exc
    return _import_data(data)


def import_encrypted_database(source: str, password: str) -> dict[str, Any]:
    from .backup_crypto import decrypt_bytes
    path = _safe_backup_path(source, create_parent=False)
    data = json.loads(decrypt_bytes(path.read_bytes(), password).decode("utf-8"))
    return _import_data(data)


def restore_encrypted_backup(source: str, destination: str, password: str) -> str:
    assert_mutation_allowed("encrypted backup restore")
    src = _safe_backup_path(source, create_parent=False)
    dst = _safe_backup_path(destination)
    tmp = dst.with_name(f".{dst.name}.restore-{os.getpid()}-{time.time_ns()}")
    try:
        decrypt_file(src, tmp, password)
        os.replace(tmp, dst)
        return str(dst)
    finally:
        tmp.unlink(missing_ok=True)


def verify_backup(source: str, password: str | None = None) -> dict[str, Any]:
    path = _safe_backup_path(source, create_parent=False)
    if password:
        from .backup_crypto import decrypt_bytes
        payload = json.loads(decrypt_bytes(path.read_bytes(), password).decode("utf-8"))
    else:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"valid": False, "type": "sqlite", "path": str(path), "size": path.stat().st_size}
    metadata = _verify_export_payload(payload)
    return {"valid": True, "type": "encrypted-json" if password else "json", "path": str(path), "size": path.stat().st_size, "metadata": metadata}

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
        ("Python list tuple", ("Python",)),
        ("SQL Server index execution plan", ("SQL Server",)),
        ("امنیت پن‌تست", ("Pentest",)),
    ]
    results = []
    reciprocal_ranks = []
    for query, expected_topics in cases:
        try:
            hits = hybrid_search(query, 5)
            ranked = [str(item.get("topic") or "") for item in hits]
            rank = next(
                (index + 1 for index, topic in enumerate(ranked)
                 if any(expected.casefold() in topic.casefold() for expected in expected_topics)),
                None,
            )
            reciprocal_ranks.append(1.0 / rank if rank else 0.0)
            results.append({
                "query": query,
                "expected_topics": list(expected_topics),
                "rank": rank,
                "top": hits[0].get("title") if hits else None,
                "passed": rank is not None,
            })
        except Exception as exc:
            reciprocal_ranks.append(0.0)
            results.append({"query": query, "expected_topics": list(expected_topics), "rank": None, "passed": False, "error": str(exc)})
    judgments = fetch_all("SELECT score,relevant FROM retrieval_judgments")
    calibration: dict[str, float | int | None]
    if judgments:
        brier = sum((float(row["relevant"]) - float(row["score"])) ** 2 for row in judgments) / len(judgments)
        buckets: dict[float, list[int]] = {}
        for row in judgments:
            bucket = round(float(row["score"]), 1)
            buckets.setdefault(bucket, []).append(int(row["relevant"]))
        ece = 0.0
        total = len(judgments)
        for bucket, labels in buckets.items():
            ece += (len(labels) / total) * abs((sum(labels) / len(labels)) - bucket)
        calibration = {"samples": total, "brier": round(brier, 6), "ece": round(ece, 6)}
    else:
        calibration = {"samples": 0, "brier": None, "ece": None}
    passed = sum(1 for x in results if x["passed"])
    return {
        "cases": results,
        "passed": passed,
        "total": len(results),
        "mrr": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 6) if reciprocal_ranks else 0.0,
        "calibration": calibration,
        "calibration_ready": int(calibration["samples"] or 0) >= 5,
    }


