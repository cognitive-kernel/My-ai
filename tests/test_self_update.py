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
