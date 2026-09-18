def test_memory_search(tmp_path,monkeypatch):
    monkeypatch.setenv("DB_PATH",str(tmp_path/"x.db"))
    import importlib
    import my_ai.config as config
    import my_ai.db as db
    import my_ai.memory as memory
    config.settings=config.Settings()
    importlib.reload(db); importlib.reload(memory)
    db.init_db(); memory.remember("Python","Test note","functions and decorators")
    assert memory.recall("functions")[0]["title"]=="Test note"
