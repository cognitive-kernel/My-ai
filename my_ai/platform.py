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


def ollama_embed(text: str, model: str = "bge-m3") -> list[float]:
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


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def hybrid_search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    limit = max(1, min(limit, 50))
    rows = fetch_all(
        """SELECT k.*, bm25(knowledge_fts) AS fts_rank
           FROM knowledge_fts JOIN knowledge k ON k.id=knowledge_fts.rowid
           WHERE knowledge_fts MATCH ?
           ORDER BY fts_rank LIMIT ?""",
        (' '.join(f'"{t}"' for t in query.replace('"',' ').split()[:12]), limit * 3),
    )
    try:
        qvec = ollama_embed(query)
    except Exception:
        qvec = []
    if qvec:
        for row in rows:
            text = f"{row.get('title','')}\n{row.get('content','')}\n{row.get('topic','')}"
            try:
                row["semantic_score"] = cosine_similarity(qvec, ollama_embed(text))
            except Exception:
                row["semantic_score"] = 0.0
    else:
        for row in rows:
            row["semantic_score"] = 0.0
    for row in rows:
        fts = 1.0 / (1.0 + max(float(row.get("fts_rank") or 0.0), 0.0))
        semantic = float(row.get("semantic_score") or 0.0)
        row["hybrid_score"] = round(0.65 * semantic + 0.35 * fts, 6)
        row["confidence"] = round(max(0.0, min(1.0, row["hybrid_score"])), 3)
    rows.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return rows[:limit]


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


def web_fetch_policy(url: str) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = urllib.robotparser.RobotFileParser(robots_url)
    try:
        parser.read()
        allowed = parser.can_fetch("My-AI", url)
    except Exception:
        allowed = False
    return {"url": url, "robots_url": robots_url, "allowed": allowed}


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


def self_update_status() -> dict[str, Any]:
    return {
        "enabled": os.getenv("MYAI_SELF_UPDATE_ENABLED", "false").lower() == "true",
        "default_policy": "deny",
        "snapshot_required": True,
        "approval_required": True,
        "rollback_required": True,
    }


def self_update_apply(_proposal: str) -> dict[str, Any]:
    # Deliberately no-op until an explicit future implementation passes all policy gates.
    return {"applied": False, "reason": "Self-update is deny-by-default and is not enabled."}
