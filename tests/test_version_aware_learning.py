from __future__ import annotations

import sqlite3

from my_ai import learner
from my_ai.infra import persistence


def _connect_factory(path):
    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    return connect


def test_knowledge_schema_tracks_version_compatibility(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "connect", _connect_factory(tmp_path / "version.db"))
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


def test_learning_experience_tracks_execution_versions(monkeypatch):
    monkeypatch.setattr(learner, "get_bool", lambda *args, **kwargs: True, raising=False)
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


def test_persistence_schema_contains_version_columns(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "connect", _connect_factory(tmp_path / "schema.db"))
    persistence.init_db()
    rows = persistence.fetch_all("PRAGMA table_info(learning_experiences)")
    columns = {row["name"] for row in rows}
    assert {"model_version", "provider", "tool_version", "skill_version", "environment_version", "compatibility"} <= columns

def test_knowledge_schema_tracks_validity_window(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, "connect", _connect_factory(tmp_path / "validity.db"))
    persistence.init_db()
    kid = persistence.remember_knowledge(
        "Python", "Temporal lesson", "Use the API.",
        "https://example.test/docs", product="python", version="3.13",
        validity_status="current", valid_from="2026-01-01", valid_until="2027-01-01",
    )
    row = persistence.fetch_all("SELECT valid_from,valid_until FROM knowledge WHERE id=?", (kid,))[0]
    assert row == {"valid_from": "2026-01-01", "valid_until": "2027-01-01"}
