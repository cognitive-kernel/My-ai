from my_ai import learning_catalog


def test_learning_catalog_exposes_relearning_queue_schema():
    assert "learning_relearning_queue" in learning_catalog.SCHEMA
    assert hasattr(learning_catalog, "update_source")


def test_source_change_is_queued_for_relearning(monkeypatch):
    row = {"id": 7, "url": "https://old.example", "content_hash": "abc", "content_version": 1, "source_type": "web", "title": "Source", "priority": 1, "weight": 1.0, "product": "", "version": "", "compatibility": "unknown", "course_id": None, "topic_id": None, "status": "active"}
    class Cursor:
        def __init__(self, value=None): self.row = value
        def fetchone(self): return self.row
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql, params=()):
            normalized = sql.strip()
            if normalized.startswith("SELECT id,url,content_hash"):
                return Cursor(row)
            if normalized.startswith("SELECT * FROM learning_source_catalog"):
                return Cursor(row | {"url": "https://new.example", "status": "recheck", "content_version": 2})
            return Cursor()
        def commit(self): pass
    monkeypatch.setattr(learning_catalog, "connect", lambda: Conn())
    monkeypatch.setattr(learning_catalog, "ensure_schema", lambda: None)
    result = learning_catalog.update_source(7, url="https://new.example")
    assert result is not None


def test_learning_source_catalog_validates_persists_reviews_and_relearning(monkeypatch, tmp_path):
    import sqlite3
    from my_ai import learning_catalog as catalog
    def connect():
        conn = sqlite3.connect(tmp_path / "learning-catalog.db")
        conn.row_factory = sqlite3.Row
        return conn
    monkeypatch.setattr(catalog, "connect", connect)
    catalog.ensure_schema()
    import pytest
    with pytest.raises(ValueError):
        catalog.add_source("https://example.test", source_type="unsupported")
    source = catalog.add_source("https://example.test/docs", source_type="official-docs", priority=10, weight=2)
    assert source["status"] == "pending"
    assert source["priority"] == 10 and source["weight"] == 2
    approved = catalog.review_source(source["id"], "approved")
    assert approved["status"] == "approved"
    catalog.update_content_hash(source["id"], "v1")
    changed = catalog.update_content_hash(source["id"], "v2")
    assert changed["relearning_queued"] is True
    assert catalog.list_relearning_queue(source_id=source["id"])