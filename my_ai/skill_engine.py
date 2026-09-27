from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from .db import execute, fetch_all


_EVIDENCE_KINDS = {"test", "benchmark", "official_source"}
_EXECUTED_KINDS = {"test", "benchmark"}


def _parse_evidence(raw: str | None) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
        return value if isinstance(value, dict) else {}
    except (TypeError, json.JSONDecodeError):
        return {}


def _evidence_scores(rows: list[dict[str, Any]]) -> dict[str, float]:
    coverage_values: list[float] = []
    test_values: list[float] = []
    benchmark_values: list[float] = []
    concept: list[float] = []
    source: list[float] = []
    reliability: list[float] = []

    for row in rows:
        details = _parse_evidence(row.get("evidence"))
        base = 100.0 if int(row.get("passed") or 0) else 0.0
        kind = str(row.get("kind") or "")
        if kind == "official_source":
            coverage_values.append(float(details.get("coverage_score", base)))
            source.append(float(details.get("source_score", base)))
        elif kind == "test":
            test_values.append(float(details.get("skill_score", base)))
            concept.append(float(details.get("concept_score", base)))
        elif kind == "benchmark":
            benchmark_values.append(float(details.get("skill_score", base)))
            reliability.append(float(details.get("reliability_score", base)))

    coverage = sum(coverage_values) / len(coverage_values) if coverage_values else 0.0
    test_score = sum(test_values) / len(test_values) if test_values else 0.0
    benchmark_score = sum(benchmark_values) / len(benchmark_values) if benchmark_values else 0.0
    executed = test_values + benchmark_values
    skill_score = sum(executed) / len(executed) if executed else 0.0
    return {
        "knowledge_coverage_score": max(0.0, min(100.0, coverage)),
        "verified_skill_score": max(0.0, min(100.0, skill_score)),
        "test_score": max(0.0, min(100.0, test_score)),
        "benchmark_score": max(0.0, min(100.0, benchmark_score)),
        "concept_score": max(0.0, min(100.0, sum(concept) / len(concept) if concept else 0.0)),
        "source_score": max(0.0, min(100.0, sum(source) / len(source) if source else 0.0)),
        "reliability_score": max(0.0, min(100.0, sum(reliability) / len(reliability) if reliability else 0.0)),
    }


def _evidence_hash_valid(details: dict[str, Any]) -> bool:
    stored = str(details.get("evidence_hash") or "")
    if not stored:
        return False
    unsigned = dict(details)
    unsigned.pop("evidence_hash", None)
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest() == stored


def _verification_state(skill: dict[str, Any], rows: list[dict[str, Any]], current_version: str | None = None) -> tuple[bool, str]:
    version = str(current_version if current_version is not None else skill["version"])
    if str(skill["version"]) != version:
        return False, "skill_version_changed"
    if not rows:
        return False, "no_evidence"

    kinds = {str(row.get("kind") or "") for row in rows}
    if not _EXECUTED_KINDS.issubset(kinds) or "official_source" not in kinds:
        return False, "insufficient_evidence_kinds"

    for row in rows:
        details = _parse_evidence(row.get("evidence"))
        if str(details.get("skill_version") or "") != version:
            return False, "stale_evidence"
        if not _evidence_hash_valid(details):
            return False, "evidence_integrity_failed"

    scores = _evidence_scores(rows)
    passed_execution = all(
        int(row.get("passed") or 0) == 1
        for row in rows
        if str(row.get("kind") or "") in _EXECUTED_KINDS
    )
    if not passed_execution:
        return False, "failed_execution_evidence"
    if scores["knowledge_coverage_score"] < 70.0:
        return False, "insufficient_knowledge_coverage"
    if scores["verified_skill_score"] < 80.0:
        return False, "insufficient_verified_skill_score"
    return True, "verified"


def _persist_scores(skill_id: int, skill: dict[str, Any], rows: list[dict[str, Any]], verified_override: bool | None = None) -> dict[str, Any]:
    scores = _evidence_scores(rows)
    verified, reason = _verification_state(skill, rows)
    if verified_override is not None:
        verified = bool(verified_override)
    execute(
        "UPDATE skills SET score=?,knowledge_coverage_score=?,verified_skill_score=?,concept_score=?,implementation_score=?,source_score=?,reliability_score=?,verified=?,last_verified=? WHERE id=?",
        (
            scores["verified_skill_score"],
            scores["knowledge_coverage_score"],
            scores["verified_skill_score"],
            scores["concept_score"],
            scores["test_score"],
            scores["source_score"],
            scores["reliability_score"],
            1 if verified else 0,
            datetime.now(timezone.utc).isoformat() if verified else None,
            skill_id,
        ),
    )
    return {
        **scores,
        "verified": verified,
        "verification_reason": reason,
        "evidence_count": len(rows),
        "evidence_kinds": len({str(row.get("kind") or "") for row in rows}),
    }


def ensure_skill(name: str, version: str = "current") -> int:
    rows = fetch_all("SELECT id FROM skills WHERE name=? AND version=?", (name, version))
    if rows:
        return int(rows[0]["id"])
    return execute(
        "INSERT INTO skills(name,version,score,verified,knowledge_coverage_score,verified_skill_score) VALUES(?,?,0,0,0,0)",
        (name, version),
    )


def record_evidence(skill_id: int, kind: str, passed: bool, details: dict[str, Any] | None = None) -> int:
    if kind not in _EVIDENCE_KINDS:
        raise ValueError("Evidence must be an executed test, benchmark, or official source.")
    if not details:
        raise ValueError("Evidence details are required.")
    if kind == "official_source":
        if not str(details.get("source_url") or "").strip():
            raise ValueError("Official-source evidence requires a non-empty source_url.")
    elif not str(details.get("command") or "").strip() or "artifact" not in details:
        raise ValueError("Executed evidence requires a command and artifact.")
    skill_rows = fetch_all("SELECT id,version FROM skills WHERE id=?", (skill_id,))
    if not skill_rows:
        raise ValueError("Skill not found.")

    skill_version = str(skill_rows[0]["version"])
    evidence_details = dict(details)
    evidence_details.setdefault("skill_version", skill_version)
    evidence_details.setdefault("observed_at", datetime.now(timezone.utc).isoformat())
    evidence_details["passed"] = bool(passed)
    canonical = json.dumps(evidence_details, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    evidence_details["evidence_hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    evidence = json.dumps(evidence_details, ensure_ascii=False, sort_keys=True)
    evidence_id = execute(
        "INSERT INTO skill_evidence(skill_id,kind,passed,evidence) VALUES(?,?,?,?)",
        (skill_id, kind, 1 if passed else 0, evidence),
    )
    skill = fetch_all("SELECT * FROM skills WHERE id=?", (skill_id,))[0]
    rows = fetch_all("SELECT kind,passed,evidence FROM skill_evidence WHERE skill_id=? ORDER BY id", (skill_id,))
    _persist_scores(skill_id, skill, rows)
    return evidence_id


def revalidate(skill_id: int, current_version: str) -> dict[str, Any]:
    rows = fetch_all("SELECT * FROM skills WHERE id=?", (skill_id,))
    if not rows:
        raise ValueError("Skill not found.")
    skill = rows[0]
    evidence_rows = fetch_all(
        "SELECT id,kind,passed,evidence,created_at FROM skill_evidence WHERE skill_id=? ORDER BY id",
        (skill_id,),
    )
    if str(skill["version"]) != str(current_version):
        execute(
            "UPDATE skills SET version=?,verified=0,score=0,verified_skill_score=0,last_verified=NULL WHERE id=?",
            (current_version, skill_id),
        )
        return {
            "revalidated": False,
            "reason": "skill_version_changed",
            "verified": False,
            "stale_evidence": len(evidence_rows),
            "evidence": evidence_snapshot(skill_id),
        }

    result = _persist_scores(skill_id, skill, evidence_rows)
    result["revalidated"] = True
    result["evidence"] = evidence_snapshot(skill_id)
    return result


def evidence_snapshot(skill_id: int) -> list[dict[str, Any]]:
    rows = fetch_all(
        "SELECT id,kind,passed,evidence,created_at FROM skill_evidence WHERE skill_id=? ORDER BY id DESC",
        (skill_id,),
    )
    result: list[dict[str, Any]] = []
    for row in rows:
        result.append(
            {
                "id": int(row["id"]),
                "kind": row["kind"],
                "passed": bool(row["passed"]),
                "created_at": row.get("created_at"),
                "details": _parse_evidence(row["evidence"]),
            }
        )
    return result


def snapshot() -> list[dict[str, Any]]:
    skills = fetch_all(
        """SELECT s.*,
                  COUNT(e.id) AS evidence_count,
                  CASE WHEN s.last_verified IS NULL
                             OR s.last_verified < datetime('now','-30 days')
                       THEN 1 ELSE 0 END AS review_due
           FROM skills s LEFT JOIN skill_evidence e ON e.skill_id=s.id
           GROUP BY s.id ORDER BY s.id DESC"""
    )
    for skill in skills:
        skill["evidence"] = evidence_snapshot(int(skill["id"]))
        skill["verification_state"] = "verified" if int(skill.get("verified") or 0) else "unverified"
        skill["knowledge_coverage_score"] = float(skill.get("knowledge_coverage_score") or 0.0)
        skill["verified_skill_score"] = float(skill.get("verified_skill_score") or skill.get("score") or 0.0)
    return skills


def record_review(skill_id: int, reviewer_id: int, outcome: str, notes: str = "") -> int:
    if outcome not in {"approved", "changes_requested", "rejected"}:
        raise ValueError("Invalid skill review outcome.")
    if not fetch_all("SELECT id FROM skills WHERE id=?", (skill_id,)):
        raise ValueError("Skill not found.")
    review_id = execute(
        "INSERT INTO skill_reviews(skill_id,reviewer_id,outcome,notes) VALUES(?,?,?,?)",
        (skill_id, reviewer_id, outcome, str(notes or "")[:4000]),
    )
    if outcome != "approved":
        execute("UPDATE skills SET verified=0,last_verified=NULL WHERE id=?", (skill_id,))
    return review_id


def review_snapshot() -> list[dict[str, Any]]:
    return fetch_all(
        """SELECT s.id,s.name,s.version,s.verified,s.score,
                  s.knowledge_coverage_score,s.verified_skill_score,s.last_verified,
                  COUNT(r.id) AS review_count,
                  MAX(r.created_at) AS last_review_at,
                  COALESCE((SELECT outcome FROM skill_reviews r2
                            WHERE r2.skill_id=s.id ORDER BY r2.id DESC LIMIT 1),'none') AS last_review_outcome
           FROM skills s LEFT JOIN skill_reviews r ON r.skill_id=s.id
           GROUP BY s.id ORDER BY s.id DESC"""
    )
