from pathlib import Path

from my_ai import self_update


def test_self_update_is_deny_by_default(monkeypatch):
    monkeypatch.delenv("MYAI_SELF_UPDATE_ENABLED", raising=False)
    monkeypatch.delenv("MYAI_SELF_UPDATE_APPROVED", raising=False)
    monkeypatch.setattr(self_update, "_git", lambda *args, **kwargs: "")
    monkeypatch.setattr(self_update, "get_setting", lambda *args: "")
    try:
        self_update.apply_confirmed_update()
    except RuntimeError as exc:
        assert "deny-by-default" in str(exc)
    else:
        raise AssertionError("self-update must require explicit enablement")


def test_health_url_rejects_non_loopback():
    for url in ("http://example.com/health", "https://127.0.0.1/health"):
        try:
            self_update._validate_health_url(url)
        except ValueError:
            pass
        else:
            raise AssertionError(url)


def test_health_url_accepts_loopback():
    assert self_update._validate_health_url("http://127.0.0.1:8000/health") == "http://127.0.0.1:8000/health"


def test_candidate_failure_is_recorded(monkeypatch):
    events = []
    monkeypatch.setattr(self_update, "_record_lesson", lambda event, **data: events.append((event, data)))
    self_update._record_lesson("candidate_test_failed", candidate="abc", details="failed")
    assert events[0][0] == "candidate_test_failed"


def test_database_snapshot_round_trip(tmp_path, monkeypatch):
    db = tmp_path / "source.sqlite"
    destination = tmp_path / "snapshot.sqlite"
    monkeypatch.setenv("DB_PATH", str(db))
    self_update.sqlite3.connect(db).execute("CREATE TABLE t(value TEXT)")
    conn = self_update.sqlite3.connect(db)
    conn.execute("INSERT INTO t VALUES ('before')")
    conn.commit(); conn.close()
    assert self_update._snapshot_database(destination) == destination
    conn = self_update.sqlite3.connect(db)
    conn.execute("UPDATE t SET value='after'"); conn.commit(); conn.close()
    self_update.restore_database_snapshot(destination, db)
    conn = self_update.sqlite3.connect(db)
    assert conn.execute("SELECT value FROM t").fetchone()[0] == "before"
    conn.close()


def test_git_rollback_uses_immutable_tag(monkeypatch):
    calls = []
    monkeypatch.setattr(self_update, "_git", lambda *args, **kwargs: calls.append(args) or ("abc123" if args == ("rev-parse", "HEAD") else ""))
    assert self_update.rollback_git_state("myai-preupdate-test") == "abc123"
    assert calls[0] == ("reset", "--hard", "myai-preupdate-test")
