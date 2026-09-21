from __future__ import annotations

import json
import hashlib
from typing import Any

from .db import execute, fetch_all


def ensure_skill(name: str, version: str = "current") -> int:
    rows=fetch_all("SELECT id FROM skills WHERE name=? AND version=?",(name,version))
    if rows: return int(rows[0]["id"])
    return execute("INSERT INTO skills(name,version,score,verified) VALUES(?,?,0,0)",(name,version))


def record_evidence(skill_id: int, kind: str, passed: bool, details: dict[str,Any] | None = None) -> int:
    evidence=json.dumps(details or {},ensure_ascii=False)
    eid=execute("INSERT INTO skill_evidence(skill_id,kind,passed,evidence) VALUES(?,?,?,?)",(skill_id,kind,1 if passed else 0,evidence))
    rows=fetch_all("SELECT AVG(passed)*100 AS score,COUNT(*) AS n FROM skill_evidence WHERE skill_id=?",(skill_id,))
    score=float(rows[0]["score"] or 0)
    verified=score >= 80 and int(rows[0]["n"] or 0) >= 2
    execute("UPDATE skills SET score=?,verified=?,last_verified=CURRENT_TIMESTAMP WHERE id=?",(score,1 if verified else 0,skill_id))
    return eid


def revalidate(skill_id: int, current_version: str) -> dict[str,Any]:
    rows=fetch_all("SELECT * FROM skills WHERE id=?",(skill_id,))
    if not rows: raise ValueError("Skill not found.")
    skill=rows[0]
    if skill["version"] != current_version:
        execute("UPDATE skills SET version=?,verified=0,score=0,last_verified=NULL WHERE id=?",(current_version,skill_id))
        return {"revalidated":False,"reason":"version_changed","verified":False}
    return {"revalidated":True,"verified":bool(skill["verified"]),"score":skill["score"]}


def snapshot() -> list[dict[str,Any]]:
    return fetch_all("""SELECT s.*,COUNT(e.id) AS evidence_count
                        FROM skills s LEFT JOIN skill_evidence e ON e.skill_id=s.id
                        GROUP BY s.id ORDER BY s.id DESC""")
