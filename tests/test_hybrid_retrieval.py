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


def test_hybrid_search_returns_mandatory_provenance_and_embedding_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "hybrid.db"))
    import importlib
    import my_ai.config as config
    import my_ai.db as db
    import my_ai.platform as platform

    config.settings = config.Settings()
    importlib.reload(db)
    importlib.reload(platform)
    db.init_db()
    db.remember_knowledge("topic", "note", "semantic retrieval text", "https://example.test/source")
    db.execute("UPDATE knowledge SET verification_status='verified' WHERE title='note'")

    monkeypatch.setattr(platform, "ollama_embed_batch", lambda texts, model=None: [[1.0, 0.0] for _ in texts])
    monkeypatch.setattr(platform, "ollama_embed", lambda text, model=None: [1.0, 0.0])
    platform.invalidate_hybrid_search_cache()

    hit = platform.hybrid_search("retrieval", 1, verified_only=True)[0]
    assert hit["hybrid_mode"] == "semantic+fts5"
    assert hit["embedding_model"] == "nomic-embed-text"
    assert hit["citation_required"] is True
    assert hit["provenance"]["citation_id"].startswith("K")
    assert hit["provenance"]["source_url"] == "https://example.test/source"
    assert hit["confidence"] is None
    assert hit["confidence_calibrated"] is False


def test_hybrid_confidence_is_empirically_calibrated_after_judgments(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "hybrid.db"))
    import importlib
    import my_ai.config as config
    import my_ai.db as db
    import my_ai.platform as platform

    config.settings = config.Settings()
    importlib.reload(db)
    importlib.reload(platform)
    db.init_db()
    item_id = db.remember_knowledge("topic", "note", "semantic retrieval text", "https://example.test/source")
    db.execute("UPDATE knowledge SET verification_status='verified' WHERE id=?", (item_id,))
    for _ in range(5):
        db.execute(
            "INSERT INTO retrieval_judgments(query,knowledge_id,relevant,score) VALUES(?,?,?,?)",
            ("retrieval", item_id, 1, 1.0),
        )

    monkeypatch.setattr(platform, "ollama_embed_batch", lambda texts, model=None: [[1.0, 0.0] for _ in texts])
    monkeypatch.setattr(platform, "ollama_embed", lambda text, model=None: [1.0, 0.0])
    platform.invalidate_hybrid_search_cache()

    hit = platform.hybrid_search("retrieval", 1, verified_only=True)[0]
    assert hit["confidence_calibrated"] is True
    assert hit["confidence_samples"] == 5
    assert 0.0 < hit["confidence"] <= 1.0
