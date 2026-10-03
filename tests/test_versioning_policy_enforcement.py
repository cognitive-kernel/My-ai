import json
import sqlite3
from contextlib import contextmanager

import pytest

from my_ai import control_plane


def _isolated(monkeypatch, tmp_path):
    db = sqlite3.connect(tmp_path / "control.db")
    db.row_factory = sqlite3.Row

    @contextmanager
    def connect():
        yield db

    monkeypatch.setattr(control_plane, "connect", connect)
    control_plane.ensure_schema()
    return db


def test_versioning_policy_requires_monotonic_payload_version(monkeypatch, tmp_path):
    db = _isolated(monkeypatch, tmp_path)
    control_plane.put_record("security.versioning", "default", {
        "required": True, "immutable_history": True, "compatibility_check": True
    })
    control_plane.put_record("agent.behavior", "policy", {"version": 1, "mode": "safe"})
    with pytest.raises(ValueError, match="payload.version=2"):
        control_plane.put_record("agent.behavior", "policy", {"version": 3, "mode": "unsafe"})
    updated = control_plane.put_record("agent.behavior", "policy", {"version": 2, "mode": "safe"})
    assert updated["version"] == 2
    history = control_plane.list_history("agent.behavior", "policy")
    assert [item["version"] for item in history[:2]] == [2, 1]
    db.close()


def test_versioning_policy_validates_compatibility_metadata(monkeypatch, tmp_path):
    db = _isolated(monkeypatch, tmp_path)
    control_plane.put_record("security.versioning", "agent.behavior", {
        "required": True, "immutable_history": True, "compatibility_check": True
    })
    with pytest.raises(ValueError, match="compatible_versions"):
        control_plane.put_record("agent.behavior", "policy", {"version": 1, "compatible_versions": [1]})
    ok = control_plane.put_record("agent.behavior", "policy", {"version": 1, "compatible_versions": ["1.x"]})
    assert ok["version"] == 1
    db.close()
