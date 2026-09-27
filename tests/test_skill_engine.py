import json

import my_ai.skill_engine as skill_engine


def test_revalidate_checks_evidence_version(monkeypatch):
    state = {
        "skills": [{"id": 1, "version": "1", "verified": 1, "score": 100}],
        "evidence": [
            {"id": 1, "kind": "test", "passed": 1, "evidence": json.dumps({"skill_version": "1", "evidence_hash": "x", "test_id": "t1"})},
            {"id": 2, "kind": "benchmark", "passed": 1, "evidence": json.dumps({"skill_version": "1", "evidence_hash": "y", "artifact": "a1"})},
            {"id": 3, "kind": "official_source", "passed": 1, "evidence": json.dumps({"skill_version": "1", "evidence_hash": "z", "source_url": "https://example.test"})},
        ],
    }

    def fetch_all(sql, params=()):
        if "FROM skills" in sql:
            return state["skills"]
        return state["evidence"]

    monkeypatch.setattr(skill_engine, "fetch_all", fetch_all)
    updates = []
    monkeypatch.setattr(skill_engine, "execute", lambda sql, params=(): updates.append((sql, params)) or 1)
    result = skill_engine.revalidate(1, "2")
    assert result["revalidated"] is False
    assert result["reason"] == "skill_version_changed"
    assert result["verified"] is False
    assert updates


def test_verification_separates_knowledge_coverage_from_skill_score(monkeypatch):
    rows = [
        {"kind": "official_source", "passed": 1, "evidence": json.dumps({"coverage_score": 95, "source_score": 90, "skill_version": "1", "evidence_hash": "a"})},
        {"kind": "test", "passed": 1, "evidence": json.dumps({"skill_score": 60, "concept_score": 80, "skill_version": "1", "evidence_hash": "b"})},
        {"kind": "benchmark", "passed": 1, "evidence": json.dumps({"skill_score": 100, "reliability_score": 100, "skill_version": "1", "evidence_hash": "c"})},
    ]
    skill = {"id": 1, "version": "1"}
    captured = []
    monkeypatch.setattr(skill_engine, "execute", lambda sql, params=(): captured.append(params) or 1)
    result = skill_engine._persist_scores(1, skill, rows)
    assert result["knowledge_coverage_score"] == 95
    assert result["verified_skill_score"] == 80
    assert result["verified"] is True
    assert captured


def test_low_knowledge_coverage_does_not_verify_skill(monkeypatch):
    rows = [
        {"kind": "official_source", "passed": 1, "evidence": json.dumps({"coverage_score": 40, "skill_version": "1", "evidence_hash": "a"})},
        {"kind": "test", "passed": 1, "evidence": json.dumps({"skill_score": 100, "skill_version": "1", "evidence_hash": "b"})},
        {"kind": "benchmark", "passed": 1, "evidence": json.dumps({"skill_score": 100, "skill_version": "1", "evidence_hash": "c"})},
    ]
    captured = []
    monkeypatch.setattr(skill_engine, "execute", lambda sql, params=(): captured.append(params) or 1)
    result = skill_engine._persist_scores(1, {"id": 1, "version": "1"}, rows)
    assert result["knowledge_coverage_score"] == 40
    assert result["verified_skill_score"] == 100
    assert result["verified"] is False
    assert result["verification_reason"] == "insufficient_knowledge_coverage"


def test_evidence_snapshot_is_visible(monkeypatch):
    monkeypatch.setattr(
        skill_engine,
        "fetch_all",
        lambda sql, params=(): [
            {"id": 7, "kind": "benchmark", "passed": 1, "evidence": json.dumps({"artifact": "run-7", "skill_version": "1"}), "created_at": "now"}
        ],
    )
    result = skill_engine.evidence_snapshot(1)
    assert result[0]["id"] == 7
    assert result[0]["details"]["artifact"] == "run-7"
