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
