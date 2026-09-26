from threading import Event

import pytest

from my_ai.learning_resilience import retry_forever


def test_retry_forever_recovers_after_transient_failures(monkeypatch):
    attempts = {"count": 0}

    def operation():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("transient")
        return "ok"

    monkeypatch.setattr("my_ai.learning_resilience.time.sleep", lambda _: None)
    result = retry_forever(None, operation, "test", stop_event=Event())
    assert result == "ok"
    assert attempts["count"] == 3


def test_retry_forever_stops_after_configured_attempts(monkeypatch):
    attempts = {"count": 0}

    def operation():
        attempts["count"] += 1
        raise RuntimeError("permanent")

    monkeypatch.setattr("my_ai.learning_resilience.time.sleep", lambda _: None)
    monkeypatch.setattr(
        "my_ai.learning_resilience.get_int",
        lambda key, default: 3 if key == "learning.max_retries" else default,
    )

    with pytest.raises(RuntimeError, match=r"failed after 3 attempts"):
        retry_forever(None, operation, "source", stop_event=Event())

    assert attempts["count"] == 3
