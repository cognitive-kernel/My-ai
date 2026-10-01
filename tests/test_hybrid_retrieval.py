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


def test_hybrid_confidence_calibration_is_monotonic(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "hybrid.db"))
    import importlib
    import my_ai.config as config
    import my_ai.db as db
    import my_ai.platform as platform
    config.settings = config.Settings()
    importlib.reload(db)
    importlib.reload(platform)
    db.init_db()
    judgments = [
        {"score": 0.2, "relevant": 0},
        {"score": 0.4, "relevant": 1},
        {"score": 0.6, "relevant": 0},
        {"score": 0.8, "relevant": 1},
        {"score": 1.0, "relevant": 1},
    ]
    curve = platform._isotonic_calibration(judgments)
    assert all(left[1] <= right[1] for left, right in zip(curve, curve[1:]))


def test_semantic_duplicate_rejects_paraphrase_and_audits(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "dup.db"))
    import importlib
    import my_ai.config as config
    import my_ai.db as db
    config.settings = config.Settings()
    importlib.reload(db)
    db.init_db()
    first = db.remember_knowledge("python", "lists", "Python lists preserve insertion order and allow duplicate values.")
    monkeypatch.setattr("my_ai.platform.ollama_embed", lambda text, model=None: [1.0, 0.0])
    monkeypatch.setattr("my_ai.platform.cosine_similarity", lambda a, b: 0.96)
    db.execute(
        "INSERT INTO knowledge_embeddings(knowledge_id,content_hash,model,embedding) VALUES(?,?,?,?)",
        (first, db.fetch_all("SELECT content_hash FROM knowledge WHERE id=?", (first,))[0]["content_hash"], config.settings.embedding_model, "[1.0,0.0]"),
    )
    import pytest
    with pytest.raises(ValueError, match="Semantic duplicate"):
        db.remember_knowledge("python", "ordered lists", "Python lists keep insertion order and can contain repeated values.")
    audit = db.fetch_all("SELECT action,details FROM knowledge_audit WHERE knowledge_id=? ORDER BY id DESC", (first,))
    assert audit[0]["action"] == "duplicate_semantic_rejected"
    assert "similarity" in audit[0]["details"]


def test_semantic_duplicate_threshold_is_configurable(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "threshold.db"))
    monkeypatch.setenv("KNOWLEDGE_DUPLICATE_THRESHOLD", "0.99")
    import importlib
    import my_ai.config as config
    import my_ai.db as db
    config.settings = config.Settings()
    importlib.reload(db)
    db.init_db()
    first = db.remember_knowledge("topic", "a", "content")
    monkeypatch.setattr("my_ai.platform.ollama_embed", lambda text, model=None: [1.0, 0.0])
    monkeypatch.setattr("my_ai.platform.cosine_similarity", lambda a, b: 0.96)
    db.execute("INSERT INTO knowledge_embeddings(knowledge_id,content_hash,model,embedding) VALUES(?,?,?,?)",
               (first, db.fetch_all("SELECT content_hash FROM knowledge WHERE id=?", (first,))[0]["content_hash"], config.settings.embedding_model, "[1.0,0.0]"))
    second = db.remember_knowledge("topic", "b", "different content")
    assert second != first
