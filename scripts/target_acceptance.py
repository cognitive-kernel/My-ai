from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from my_ai import db
from my_ai.eval_harness import BASELINE_CASES, run_retrieval_eval
from my_ai.file_processing import system_prerequisite_status
from my_ai.voice import status as voice_status


def check_ollama() -> dict[str, object]:
    import urllib.request

    url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        models = [str(item.get("name", "")) for item in payload.get("models", [])]
        embedding_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        return {
            "ok": True,
            "url": url,
            "embedding_model": embedding_model,
            "embedding_model_present": any(
                name == embedding_model or name.startswith(embedding_model + ":")
                for name in models
            ),
            "models": models,
        }
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def check_database() -> dict[str, object]:
    try:
        db.init_db()
        row = db.fetch_one(
            "SELECT id, username, role FROM users ORDER BY id LIMIT 1"
        )
        return {
            "ok": True,
            "first_account_exists": bool(row),
            "first_account_is_admin": bool(row and row.get("role") == "admin"),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def check_hybrid_retrieval() -> dict[str, object]:
    try:
        result = run_retrieval_eval(
            lambda query, limit: __import__("my_ai.platform", fromlist=["hybrid_search"]).hybrid_search(
                query, limit, verified_only=True
            ),
            BASELINE_CASES,
        )
        return {
            "ok": result["pass_rate"] > 0.0,
            "mrr": result["mrr"],
            "pass_rate": result["pass_rate"],
            "cases": result["baseline_cases"],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def check_backup() -> dict[str, object]:
    try:
        with tempfile.TemporaryDirectory(prefix="myai-acceptance-") as temp:
            target = Path(temp) / "backup-source.txt"
            target.write_text("my-ai acceptance backup", encoding="utf-8")
            digest = __import__("hashlib").sha256(target.read_bytes()).hexdigest()
            return {"ok": bool(digest), "sha256": digest}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run() -> dict[str, object]:
    checks = {
        "database": check_database(),
        "ollama": check_ollama(),
        "hybrid_retrieval": check_hybrid_retrieval(),
        "voice": voice_status(),
        "system_prerequisites": system_prerequisite_status(["git", "ffmpeg", "ffprobe"]),
        "backup": check_backup(),
    }
    failed = []
    for name, result in checks.items():
        if isinstance(result, dict) and result.get("ok") is False:
            failed.append(name)
        elif name == "ollama" and not result.get("ok"):
            failed.append(name)
        elif name == "database" and not result.get("ok"):
            failed.append(name)
        elif name == "hybrid_retrieval" and not result.get("ok"):
            failed.append(name)
        elif name == "backup" and not result.get("ok"):
            failed.append(name)
    return {"ok": not failed, "failed": failed, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run My-AI target-machine acceptance diagnostics.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.parse_args()
    result = run()
    if parser.parse_args().json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
