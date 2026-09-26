from __future__ import annotations

import json
from typing import Any

from .db import execute, fetch_all


def ensure_skill(name: str, version: str = "current") -> int:
    rows=fetch_all("SELECT id FROM skills WHERE name=? AND version=?",(name,version))
    if rows: return int(rows[0]["id"])
    return execute("INSERT INTO skills(name,version,score,verified) VALUES(?,?,0,0)",(name,version))


def record_evidence(skill_id: int, kind: str, passed: bool, details: dict[str,Any] | None = None) -> int:
    if kind not in {"test","benchmark","official_source"}:
        raise ValueError("Evidence must be an executed test, benchmark, or official source.")
    if not details or not any(key in details for key in ("command","source_url","test_id","artifact")):
        raise ValueError("Evidence requires a command, source_url, test_id, or artifact reference.")
    skill_rows=fetch_all("SELECT version FROM skills WHERE id=?",(skill_id,))
    if not skill_rows:
        raise ValueError("Skill not found.")
    evidence_details=dict(details)
    evidence_details.setdefault("skill_version", str(skill_rows[0]["version"]))
    evidence=json.dumps(evidence_details,ensure_ascii=False)
    eid=execute("INSERT INTO skill_evidence(skill_id,kind,passed,evidence) VALUES(?,?,?,?)",(skill_id,kind,1 if passed else 0,evidence))
    rows=fetch_all("SELECT kind,passed,evidence FROM skill_evidence WHERE skill_id=?",(skill_id,))
    score=sum(int(row["passed"] or 0) for row in rows) / len(rows) * 100 if rows else 0.0
    metrics: dict[str, list[float]] = {"concept": [], "implementation": [], "source": [], "reliability": []}
    for row in rows:
        try:
            details=json.loads(row["evidence"] or "{}")
        except (TypeError,json.JSONDecodeError):
            details={}
        base=100.0 if int(row["passed"] or 0) else 0.0
        key={"official_source":"source","test":"implementation","benchmark":"reliability"}.get(row["kind"],"concept")
        metrics[key].append(float(details.get(f"{key}_score",base)))
        if row["kind"]=="test":
            metrics["concept"].append(float(details.get("concept_score",base)))
    values={key:(sum(vals)/len(vals) if vals else 0.0) for key,vals in metrics.items()}
    verified=score >= 80 and len(rows) >= 2 and len({row["kind"] for row in rows}) >= 2
    execute("UPDATE skills SET score=?,concept_score=?,implementation_score=?,source_score=?,reliability_score=?,verified=?,last_verified=CURRENT_TIMESTAMP WHERE id=?",
            (score,values["concept"],values["implementation"],values["source"],values["reliability"],1 if verified else 0,skill_id))
    return eid


def revalidate(skill_id: int, current_version: str) -> dict[str,Any]:
    rows=fetch_all("SELECT * FROM skills WHERE id=?",(skill_id,))
    if not rows:
        raise ValueError("Skill not found.")
    skill=rows[0]
    evidence_rows=fetch_all("SELECT kind,passed,evidence FROM skill_evidence WHERE skill_id=?",(skill_id,))
    stale=skill["version"] != current_version
    if not stale:
        for row in evidence_rows:
            try:
                details=json.loads(row["evidence"] or "{}")
            except (TypeError, json.JSONDecodeError):
                details={}
            if str(details.get("skill_version") or "") != str(current_version):
                stale=True
                break
    if stale:
        execute("UPDATE skills SET version=?,verified=0,score=0,last_verified=NULL WHERE id=?",(current_version,skill_id))
        return {"revalidated":False,"reason":"evidence_stale","verified":False,"stale_evidence":len(evidence_rows)}
    passed=sum(1 for row in evidence_rows if int(row["passed"] or 0))
    kinds=len({row["kind"] for row in evidence_rows})
    score=(passed / len(evidence_rows) * 100.0) if evidence_rows else 0.0
    verified=score >= 80.0 and len(evidence_rows) >= 2 and kinds >= 2
    metrics={"concept": [], "implementation": [], "source": [], "reliability": []}
    for row in evidence_rows:
        try:
            details=json.loads(row["evidence"] or "{}")
        except (TypeError,json.JSONDecodeError):
            details={}
        base=100.0 if int(row["passed"] or 0) else 0.0
        key={"official_source":"source","test":"implementation","benchmark":"reliability"}.get(row["kind"],"concept")
        metrics[key].append(float(details.get(f"{key}_score",base)))
        if row["kind"]=="test":
            metrics["concept"].append(float(details.get("concept_score",base)))
    values={key:(sum(vals)/len(vals) if vals else 0.0) for key,vals in metrics.items()}
    execute("UPDATE skills SET score=?,concept_score=?,implementation_score=?,source_score=?,reliability_score=?,verified=?,last_verified=CURRENT_TIMESTAMP WHERE id=?",
            (score,values["concept"],values["implementation"],values["source"],values["reliability"],1 if verified else 0,skill_id))
    return {"revalidated":True,"verified":verified,"score":score,"concept_score":values["concept"],"implementation_score":values["implementation"],"source_score":values["source"],"reliability_score":values["reliability"],"evidence_count":len(evidence_rows),"evidence_kinds":kinds}


def snapshot() -> list[dict[str,Any]]:
    return fetch_all("""SELECT s.*,COUNT(e.id) AS evidence_count
                        FROM skills s LEFT JOIN skill_evidence e ON e.skill_id=s.id
                        GROUP BY s.id ORDER BY s.id DESC""")
