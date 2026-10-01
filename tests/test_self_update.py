import pytest

from my_ai import self_update


def test_update_check_detects_remote_revision(monkeypatch):
    values = iter(["", "", "local-sha", "remote-sha"])
    monkeypatch.setattr(self_update, "_git", lambda *args, **kwargs: next(values))
    result = self_update.check_for_update()
    assert result["ok"] is True
    assert result["update_available"] is True


def test_update_refuses_dirty_worktree(monkeypatch):
    monkeypatch.setattr(self_update, "_git", lambda *args, **kwargs: "local-change")
    with pytest.raises(RuntimeError, match="تغییرات محلی"):
        self_update.apply_confirmed_update()


def test_update_status_exposes_explicit_policy(monkeypatch):
    values = iter(["main", "head", ""])
    monkeypatch.setattr(self_update, "_git", lambda *args, **kwargs: next(values))
    monkeypatch.setattr(self_update, "get_bool", lambda key, default=False: False)
    result = self_update.status()
    assert result["policy"]["deny_by_default"] is True
    assert result["policy"]["ready"] is False


def test_database_snapshot_is_restorable(tmp_path, monkeypatch):
    import sqlite3
    source = tmp_path / "source.sqlite"
    snapshot = tmp_path / "snapshot.sqlite"
    conn = sqlite3.connect(source)
    conn.execute("CREATE TABLE sample(value TEXT)")
    conn.execute("INSERT INTO sample(value) VALUES('before')")
    conn.commit()
    conn.close()
    monkeypatch.setenv("DB_PATH", str(source))
    assert self_update._snapshot_database(snapshot) == snapshot
    conn = sqlite3.connect(source)
    conn.execute("DELETE FROM sample")
    conn.commit()
    conn.close()
    snapshot_conn = sqlite3.connect(snapshot)
    assert snapshot_conn.execute("SELECT value FROM sample").fetchone()[0] == "before"
    snapshot_conn.close()


def test_apply_update_runs_isolated_tests_before_activation(monkeypatch, tmp_path):
    calls = []
    state = iter(["", "current", "remote"])
    monkeypatch.setattr(self_update, "ROOT", tmp_path)
    monkeypatch.setattr(self_update, "STATE_DIR", tmp_path / "self-repair")
    self_update.STATE_DIR.mkdir()
    monkeypatch.setattr(self_update, "_git", lambda *args, **kwargs: calls.append(args) or next(state, "ok"))
    monkeypatch.setattr(self_update, "_snapshot_database", lambda destination: None)
    monkeypatch.setattr(self_update, "_tests", lambda cwd: (True, "passed"))
    monkeypatch.setattr(self_update, "_policy_flag", lambda *args: True)
    monkeypatch.setattr(self_update, "record_decision", lambda *args, **kwargs: None)
    monkeypatch.setattr(self_update, "notify", lambda *args, **kwargs: None)
    class Proc:
        @staticmethod
        def Popen(*args, **kwargs):
            calls.append(("watchdog", args[0]))
    monkeypatch.setattr(self_update.subprocess, "Popen", Proc.Popen)
    monkeypatch.setattr(self_update, "assert_write_allowed", lambda *args: None)
    result = self_update.apply_confirmed_update()
    assert result["status"] == "activated"
    assert any(args[:3] == ("worktree", "add", "--detach") for args in calls)
    assert any(args[:2] == ("merge", "--ff-only") for args in calls)
    assert result["watchdog"] is True
