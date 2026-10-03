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


def test_knowledge_export_supports_selected_ids(monkeypatch):
    from my_ai import api
    monkeypatch.setattr(api, "require_admin", lambda request: {"id": 1, "role": "admin"})
    monkeypatch.setattr(api, "fetch_all", lambda query, params=(): [{"id": 2, "title": "two"}] if "id IN" in query else [])
    result = api.knowledge_export(object(), ids="2")
    assert result["items"] == [{"id": 2, "title": "two"}]


def test_knowledge_selective_delete_updates_all_selected(monkeypatch):
    from my_ai import api
    calls = []
    monkeypatch.setattr(api, "require_admin", lambda request: {"id": 7, "role": "admin"})
    monkeypatch.setattr(api, "fetch_all", lambda query, params=(): [{"id": 2}, {"id": 4}] if "SELECT id FROM knowledge" in query else [])
    monkeypatch.setattr(api, "execute", lambda query, params=(): calls.append((query, params)))
    monkeypatch.setattr(api, "audit", lambda *args: None)
    result = api.knowledge_delete_selected(object(), ids="2,4")
    assert result == {"deleted": [2, 4], "count": 2}
    assert any("UPDATE knowledge SET verification_status='deleted'" in query for query, _ in calls)
    assert sum("knowledge_audit" in query for query, _ in calls) == 2
