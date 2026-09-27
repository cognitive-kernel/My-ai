import pytest


def test_read_only_blocks_runtime_db_mutation(monkeypatch):
    from my_ai import db
    monkeypatch.setattr(db, "_write_blocked", lambda: True)
    with pytest.raises(PermissionError, match="MYAI_READ_ONLY"):
        db.execute("INSERT INTO schema_meta(key,value) VALUES(?,?)", ("test", "x"))


def test_read_only_blocks_direct_knowledge_writer(monkeypatch):
    from my_ai import db
    monkeypatch.setattr(db, "_write_blocked", lambda: True)
    with pytest.raises(PermissionError, match="MYAI_READ_ONLY"):
        db.remember_knowledge("topic", "title", "content")
