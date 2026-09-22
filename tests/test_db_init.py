from my_ai import db


def test_knowledge_fts_rebuild_is_one_time(tmp_path, monkeypatch):
    monkeypatch.setattr(db.settings, "db_path", str(tmp_path / "test.db"))
    db.init_db()
    first = db.fetch_all("SELECT key FROM schema_meta WHERE key='knowledge_fts_rebuilt_v1'")
    db.init_db()
    second = db.fetch_all("SELECT key FROM schema_meta WHERE key='knowledge_fts_rebuilt_v1'")
    assert first and second
