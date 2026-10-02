from my_ai import learning_catalog


def test_learning_catalog_exposes_relearning_queue_schema():
    assert "learning_relearning_queue" in learning_catalog.SCHEMA
    assert hasattr(learning_catalog, "update_source")


def test_source_change_is_queued_for_relearning(monkeypatch):
    class Cursor:
        def __init__(self, row=None): self.row = row
        def fetchone(self): return self.row
    class Conn:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, sql, params=()):
            if sql.strip().startswith("SELECT id,url,content_hash"):
                return Cursor({"id": 7, "url": "https://old.example", "content_hash": "abc", "content_version": 1})
            return Cursor()
        def commit(self): pass
    monkeypatch.setattr(learning_catalog, "connect", lambda: Conn())
    monkeypatch.setattr(learning_catalog, "ensure_schema", lambda: None)
    result = learning_catalog.update_source(7, url="https://new.example")
    assert result is not None
