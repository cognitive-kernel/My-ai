import json

import my_ai.skill_engine as skill_engine


def test_revalidate_checks_evidence_version(monkeypatch):
    state = {
        "skills": [{"id": 1, "version": "1", "verified": 1, "score": 100}],
        "evidence": [
            {"kind": "test", "passed": 1, "evidence": json.dumps({"skill_version": "1", "test_id": "t1"})},
            {"kind": "benchmark", "passed": 1, "evidence": json.dumps({"skill_version": "1", "artifact": "a1"})},
        ],
    }
    def fetch_all(sql, params=()):
        return state["skills"] if "FROM skills" in sql else state["evidence"]
    monkeypatch.setattr(skill_engine, "fetch_all", fetch_all)
    updates = []
    monkeypatch.setattr(skill_engine, "execute", lambda sql, params=(): updates.append((sql, params)) or 1)
    result = skill_engine.revalidate(1, "2")
    assert result["revalidated"] is False
    assert result["reason"] == "evidence_stale"
    assert result["verified"] is False
    assert updates
