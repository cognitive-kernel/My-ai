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


def test_memory_remove_and_replace_do_not_leave_stale_results(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "mutation.db"))
    import importlib
    import my_ai.config as config
    import my_ai.db as db
    import my_ai.memory as memory
    config.settings = config.Settings()
    importlib.reload(db)
    importlib.reload(memory)
    db.init_db()

    first_id = memory.remember("Python", "Stable concept", "quartzalpha unique behavior")
    db.execute("UPDATE knowledge SET verification_status='verified' WHERE id=?", (first_id,))
    assert memory.recall("quartzalpha")[0]["id"] == first_id

    db.execute("UPDATE knowledge SET content=? WHERE id=?", ("replacement omega behavior", first_id))
    memory._recall_cached.cache_clear()
    assert memory.recall("quartzalpha") == []
    assert memory.recall("omega")[0]["id"] == first_id

    db.execute("DELETE FROM knowledge WHERE id=?", (first_id,))
    memory._recall_cached.cache_clear()
    assert memory.recall("omega") == []


def test_memory_addition_does_not_change_unrelated_query(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "isolation.db"))
    import importlib
    import my_ai.config as config
    import my_ai.db as db
    import my_ai.memory as memory
    config.settings = config.Settings()
    importlib.reload(db)
    importlib.reload(memory)
    db.init_db()

    first_id = memory.remember("Python", "Alpha", "unrelatedalpha only")
    db.execute("UPDATE knowledge SET verification_status='verified' WHERE id=?", (first_id,))
    before = memory.recall("unrelatedalpha")
    assert [x["id"] for x in before] == [first_id]

    second_id = memory.remember("Rust", "Beta", "unrelatedbeta only")
    db.execute("UPDATE knowledge SET verification_status='verified' WHERE id=?", (second_id,))
    after = memory.recall("unrelatedalpha")
    assert [x["id"] for x in after] == [first_id]
