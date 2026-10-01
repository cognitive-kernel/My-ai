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

BACKUP_FORMAT_VERSION = 4
BACKUP_CORE_TABLES = (
    "chat_sessions", "conversations", "chat_attachments", "knowledge",
    "knowledge_embeddings", "learning_sessions", "learning_runtime",
    "learning_workers", "experiments", "project_tasks", "agent_runs",
    "generated_projects", "help_updates", "security_scans",
    "learning_review_runs", "schema_meta", "fix_attempts", "retrieval_judgments",
    "knowledge_audit", "skills", "skill_reviews", "skill_evidence",
    "learning_domains", "learning_source_history", "learning_experiences", "custom_courses",
)
BACKUP_SENSITIVE_TABLES = ("users", "tool_permissions", "audit_log", "decision_log")


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


def _isotonic_calibration(judgments: list[dict[str, Any]]) -> list[tuple[float, float, int]]:
    """Fit a monotonic empirical P(relevant | retrieval score) without extra dependencies."""
    points = sorted(
        (max(0.0, min(1.0, float(row["score"] or 0.0))), int(bool(row["relevant"])))
        for row in judgments
    )
    grouped: list[list[float | int]] = []
    for score, label in points:
        if grouped and grouped[-1][0] == score:
            grouped[-1][2] = int(grouped[-1][2]) + 1
            grouped[-1][3] = int(grouped[-1][3]) + label
        else:
            grouped.append([score, score, 1, label])
    groups: list[list[float | int]] = grouped
    changed = True
    while changed and len(groups) >= 2:
        changed = False
        for index in range(len(groups) - 1):
            left, right = groups[index], groups[index + 1]
            left_mean = float(left[3]) / int(left[2])
            right_mean = float(right[3]) / int(right[2])
            if left_mean <= right_mean:
                continue
            left[1] = right[1]
            left[2] = int(left[2]) + int(right[2])
            left[3] = int(left[3]) + int(right[3])
            groups.pop(index + 1)
            changed = True
            break
    return [
        (float((group[0] + group[1]) / 2.0), float(group[3]) / int(group[2]), int(group[2]))
        for group in groups
    ]


def _calibrated_confidence(score: float, judgments: list[dict[str, Any]]) -> tuple[float | None, int]:
    if len(judgments) < 5:
        return None, 0
    curve = _isotonic_calibration(judgments)
    if not curve:
        return None, 0
    if score <= curve[0][0]:
        return round(curve[0][1], 6), curve[0][2]
    if score >= curve[-1][0]:
        return round(curve[-1][1], 6), curve[-1][2]
    for left, right in zip(curve, curve[1:]):
        if left[0] <= score <= right[0]:
            span = right[0] - left[0]
            ratio = (score - left[0]) / span if span else 0.0
            value = left[1] + ratio * (right[1] - left[1])
            return round(max(0.0, min(1.0, value)), 6), left[2] + right[2]
    return None, 0


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
    if missing_rows and os.getenv("MYAI_READ_ONLY", "false").strip().lower() != "true":
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

    judgments = [dict(row) for row in fetch_all("SELECT score,relevant FROM retrieval_judgments")]

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

        confidence, samples = _calibrated_confidence(float(row["hybrid_score"]), judgments)
        row["confidence"] = confidence
        row["confidence_calibrated"] = confidence is not None
        row["confidence_samples"] = samples
        row["confidence_basis"] = (
            "isotonic empirical calibration over persisted retrieval judgments"
            if confidence is not None
            else "uncalibrated; fewer than 5 persisted retrieval judgments"
        )

        row["embedding_model"] = settings.embedding_model
        row["semantic_available"] = bool(qvec)
        row["hybrid_mode"] = "semantic+fts5" if qvec else "fts5-only"
        if embedding_error:
            row["embedding_error"] = embedding_error[:500]

    # Never return a zero-score fallback item as relevant knowledge. This keeps
    # an unrelated/newly-added knowledge record from contaminating a query simply
    # because the result set contains fewer than `limit` relevant records.
    relevant_rows = [row for row in rows if float(row.get("hybrid_score") or 0.0) > 0.0]
    return sorted(relevant_rows, key=lambda item: item["hybrid_score"], reverse=True)[:limit]

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
