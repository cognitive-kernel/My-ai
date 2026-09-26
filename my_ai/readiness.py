from __future__ import annotations

from typing import Any

from .db import fetch_all
from .runtime_prerequisites import runtime_status
from .self_update import status as self_update_status
from .skill_engine import snapshot


def build_readiness() -> dict[str, Any]:
    runtime = runtime_status()
    knowledge = fetch_all(
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN verification_status='verified' THEN 1 ELSE 0 END) AS verified "
        "FROM knowledge"
    )[0]
    judgments = fetch_all("SELECT COUNT(*) AS total FROM retrieval_judgments")[0]
    skills = snapshot()
    due_skills = sum(1 for item in skills if int(item.get("review_due") or 0))
    self_update = self_update_status()
    checks = {
        "runtime_dependencies": bool(runtime["ok"]),
        "verified_knowledge": int(knowledge["verified"] or 0) > 0,
        "retrieval_judgments": int(judgments["total"] or 0) >= 5,
        "skills_reviewed": bool(skills) and due_skills == 0,
        "self_update_policy": bool((self_update.get("policy") or {}).get("ready")),
    }
    return {
        "ok": all(checks.values()),
        "checks": checks,
        "runtime": runtime,
        "knowledge": {"total": int(knowledge["total"] or 0), "verified": int(knowledge["verified"] or 0)},
        "retrieval_judgments": int(judgments["total"] or 0),
        "skills": {"total": len(skills), "review_due": due_skills},
        "self_update": self_update,
        "note": "This is an acceptance gate; it does not fabricate local hardware, voice, or admin evidence.",
    }
