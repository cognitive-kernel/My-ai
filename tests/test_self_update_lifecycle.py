import sqlite3
from pathlib import Path

from my_ai import self_update


def test_database_snapshot_restore_round_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "state.db"
    con = sqlite3.connect(db_path)
    con.execute("CREATE TABLE state(value TEXT)")
    con.execute("INSERT INTO state VALUES('before')")
    con.commit(); con.close()
    monkeypatch.setenv("DB_PATH", str(db_path))
    snapshot = self_update._snapshot_database(tmp_path / "snapshot.sqlite")
    assert snapshot and snapshot.exists()
    con = sqlite3.connect(db_path); con.execute("UPDATE state SET value='after'"); con.commit(); con.close()
    self_update.restore_database_snapshot(snapshot, db_path)
    con = sqlite3.connect(db_path)
    assert con.execute("SELECT value FROM state").fetchone()[0] == "before"
    con.close()


def test_health_url_is_loopback_only():
    assert self_update._validate_health_url("http://127.0.0.1:8000/health")
    for value in ("https://127.0.0.1/health", "http://example.com/health"):
        try:
            self_update._validate_health_url(value)
        except ValueError:
            continue
        raise AssertionError(value)
