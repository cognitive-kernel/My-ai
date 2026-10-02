from __future__ import annotations

from my_ai import learner
from my_ai.infra import persistence


def test_knowledge_schema_tracks_version_compatibility(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence.settings, "db_path", str(tmp_path / "version.db"))
    persistence.init_db()
    kid = persistence.remember_knowledge(
        "Python",
        "Versioned lesson",
        "Use the current API.",
        "https://example.test/docs",
        product="python",
        version="3.13",
        validity_status="current",
        compatibility="compatible",
    )
    rows = persistence.fetch_all(
        "SELECT product,version,validity_status,compatibility FROM knowledge WHERE id=?",
        (kid,),
    )
    assert rows[0] == {
        "product": "python",
        "version": "3.13",
        "validity_status": "current",
        "compatibility": "compatible",
    }


def test_learning_experience_tracks_execution_versions(tmp_path, monkeypatch):
    monkeypatch.setattr(learner, "execute", lambda sql, params=(): 1)
    # Exercise the SQL contract without depending on the application's shared DB.
    captured = []
    monkeypatch.setattr(learner, "execute", lambda sql, params=(): captured.append((sql, params)) or 1)
    monkeypatch.setattr(learner, "fetch_all", lambda *args, **kwargs: [])
    learner.LearningEngine.record_experience(
        "Python",
        "APIs",
        "lesson",
        "learn",
        "lesson evidence",
        model_version="model-v2",
        provider="provider-a",
        tool_version="tool-v3",
        skill_version="skill-v4",
        environment_version="env-v1",
        compatibility="compatible",
    )
    insert = next(item for item in captured if "INSERT INTO learning_experiences" in item[0])
    assert insert[1][-6:] == (
        "model-v2",
        "provider-a",
        "tool-v3",
        "skill-v4",
        "env-v1",
        "compatible",
    )
