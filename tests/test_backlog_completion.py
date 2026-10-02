import json

from my_ai import db
from my_ai.access_policy import PATH_ACTIONS, PUBLIC_PATHS, permission_for_path
from my_ai.skill_engine import ensure_skill, record_evidence, revalidate, snapshot


def test_sensitive_route_policy_is_explicit_and_non_public():
    sensitive = {path for method, path in PATH_ACTIONS if method in {"POST", "PUT", "PATCH", "DELETE"}}
    assert sensitive
    assert sensitive.isdisjoint(PUBLIC_PATHS)
    assert all(permission_for_path(path, method) for method, path in PATH_ACTIONS)


def test_skill_lifecycle_invalidates_stale_evidence(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "skills.db"))
    db.init_db()
    try:
        skill_id = ensure_skill("Python", "1.0")
        base = {"command": "pytest tests/test_python.py", "artifact": "artifact-1", "skill_score": 90, "coverage_score": 90, "source_score": 90, "reliability_score": 90}
        official = {"source_url": "https://docs.python.org/3/", "coverage_score": 90, "source_score": 90}
        record_evidence(skill_id, "test", True, base)
        record_evidence(skill_id, "benchmark", True, {**base, "artifact": "benchmark-1"})
        record_evidence(skill_id, "official_source", True, official)
        result = revalidate(skill_id, "2.0")
        assert result["verified"] is False
        assert result["reason"] == "skill_version_changed"
        assert snapshot()[0]["verified"] is False
    finally:
        object.__setattr__(db.settings, "db_path", old)


def test_skill_evidence_hash_is_stored_and_verifiable(tmp_path):
    old = db.settings.db_path
    object.__setattr__(db.settings, "db_path", str(tmp_path / "evidence.db"))
    db.init_db()
    try:
        skill_id = ensure_skill("Rust", "1.0")
        record_evidence(skill_id, "test", True, {"command": "pytest", "artifact": "x", "skill_score": 90})
        raw = db.fetch_all("SELECT evidence FROM skill_evidence WHERE skill_id=?", (skill_id,))[0]["evidence"]
        details = json.loads(raw)
        assert details["evidence_hash"]
        assert details["skill_version"] == "1.0"
        assert details["observed_at"]
    finally:
        object.__setattr__(db.settings, "db_path", old)
