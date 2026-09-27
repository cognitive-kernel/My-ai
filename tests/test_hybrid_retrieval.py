def test_hybrid_search_can_filter_unverified_knowledge(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "hybrid.db"))
    import importlib
    import my_ai.config as config
    import my_ai.db as db
    import my_ai.platform as platform

    config.settings = config.Settings()
    importlib.reload(db)
    importlib.reload(platform)
    db.init_db()

    db.remember_knowledge("verified-topic", "verified note", "semantic functions")
    db.remember_knowledge("draft-topic", "draft note", "semantic functions")
    db.execute("UPDATE knowledge SET verification_status='verified' WHERE title='verified note'")

    hits = platform.hybrid_search("functions", 10, verified_only=True)
    titles = {row["title"] for row in hits}
    assert "verified note" in titles
    assert "draft note" not in titles
