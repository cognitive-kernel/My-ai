def test_memory_search(tmp_path,monkeypatch):
    monkeypatch.setenv("DB_PATH",str(tmp_path/"x.db"))
    import importlib
    import my_ai.config as config
    import my_ai.db as db
    import my_ai.memory as memory
    config.settings=config.Settings()
    importlib.reload(db); importlib.reload(memory)
    db.init_db(); memory.remember("Python","Test note","functions and decorators")
    db.execute("UPDATE knowledge SET verification_status=? WHERE title=?", ("verified", "Test note"))
    assert memory.recall("functions")[0]["title"]=="Test note"


def test_memory_update_removes_normalized_fts_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "x.db"))
    import importlib
    import my_ai.config as config
    import my_ai.db as db
    config.settings = config.Settings()
    importlib.reload(db)
    db.init_db()
    item_id = db.remember_knowledge("test", "old", "word old")
    assert db.search_knowledge("word")
    db.execute("UPDATE knowledge SET content=? WHERE id=?", ("new content", item_id))
    assert db.search_knowledge("word") == []


def test_memory_retention_cleanup_uses_setting(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH",str(tmp_path/"retention.db"))
    import importlib
    import my_ai.config as config
    import my_ai.db as db
    import my_ai.infra.persistence as persistence
    import my_ai.settings_store as ss
    config.settings=config.Settings()
    importlib.reload(db); importlib.reload(persistence)
    db.init_db(); item=db.remember_knowledge("test","old","old content")
    db.execute("UPDATE knowledge SET created_at=datetime('now','-400 days') WHERE id=?",(item,))
    monkeypatch.setattr(ss,"get_int",lambda key,default: 365)
    assert persistence.purge_expired_knowledge() == 1
