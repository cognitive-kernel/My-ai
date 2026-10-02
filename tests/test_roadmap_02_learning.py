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
