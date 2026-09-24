from threading import Event

from my_ai.learning_resilience import retry_forever


def test_retry_forever_recovers_after_transient_failures():
    attempts = {"count": 0}

    def operation():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("transient")
        return "ok"

    result = retry_forever(None, operation, "test", stop_event=Event())
    assert result == "ok"
    assert attempts["count"] == 3
