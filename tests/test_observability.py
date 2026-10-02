import logging


def test_json_formatter_keeps_correlation_fields():
    from my_ai.observability import JsonLogFormatter
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "request", (), None)
    record.request_id = "abc123"
    record.method = "GET"
    record.path = "/health"
    record.status = 200
    record.duration_ms = 1.5
    value = JsonLogFormatter().format(record)
    assert '"request_id":"abc123"' in value
    assert '"path":"/health"' in value


def test_log_destination_uses_safe_file_path(tmp_path, monkeypatch):
    import my_ai.observability as observability
    import my_ai.settings_store as settings_store
    target = tmp_path / "my-ai.log"
    monkeypatch.setattr(settings_store, "get_setting", lambda key, default="": f"file:{target}" if key == "observability.log_destination" else default)
    monkeypatch.setattr(observability.Path, "cwd", classmethod(lambda cls: tmp_path))
    root = logging.getLogger()
    before = list(root.handlers)
    try:
        observability.configure_logging()
        assert any(isinstance(handler, logging.FileHandler) for handler in root.handlers)
    finally:
        for handler in list(root.handlers):
            if handler not in before and isinstance(handler, logging.FileHandler):
                handler.close()
                root.removeHandler(handler)
