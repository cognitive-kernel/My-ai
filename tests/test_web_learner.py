import pytest

from my_ai.web_learner import WebLearner


def test_web_learner_rejects_invalid_scheme():
    with pytest.raises(ValueError):
        WebLearner().fetch("file:///tmp/test.txt")


def test_web_rate_limit_tracks_hosts(monkeypatch):
    from my_ai.web_learner import WebLearner
    WebLearner._last_fetch.clear()
    WebLearner._min_interval = 0
    WebLearner._rate_limit("example.com")
    assert "example.com" in WebLearner._last_fetch


def test_robots_4xx_is_not_treated_as_disallow(monkeypatch):
    import httpx
    class FakeClient:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get(self, url): return httpx.Response(403, request=httpx.Request("GET", url))
    monkeypatch.setattr("my_ai.web_learner.pinned_client", lambda **kwargs: FakeClient())
    assert WebLearner()._robots_allowed("https://developer.android.com/guide") is True


def test_robots_5xx_fails_closed(monkeypatch):
    import httpx
    class FakeClient:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def get(self, url): return httpx.Response(503, request=httpx.Request("GET", url))
    monkeypatch.setattr("my_ai.web_learner.pinned_client", lambda **kwargs: FakeClient())
    assert WebLearner()._robots_allowed("https://example.com/page") is False


def test_retry_after_header_is_honored():
    import httpx
    response = httpx.Response(429, headers={"Retry-After": "7"}, request=httpx.Request("GET", "https://example.com"))
    assert WebLearner._retry_delay(0, response) == 7.0


def test_backoff_has_jitter_and_cap(monkeypatch):
    monkeypatch.setattr("my_ai.web_learner.random.uniform", lambda low, high: high)
    WebLearner._max_backoff = 3.0
    assert WebLearner._retry_delay(10) == 3.0


def test_failure_circuit_breaker(monkeypatch):
    WebLearner._host_failures.clear()
    WebLearner._host_last_failure.clear()
    WebLearner._failure_threshold = 2
    WebLearner._failure_cooldown = 60.0
    WebLearner._record_failure("blocked.example")
    WebLearner._record_failure("blocked.example")
    monkeypatch.setattr("my_ai.web_learner.time.monotonic", lambda: WebLearner._host_last_failure["blocked.example"] + 1)
    with pytest.raises(RuntimeError, match="temporarily blocked"):
        WebLearner._rate_limit("blocked.example")
    WebLearner._failure_threshold = 10


def test_success_resets_failure_state():
    WebLearner._host_failures["example.com"] = 4
    WebLearner._host_last_failure["example.com"] = 1.0
    WebLearner._record_success("example.com")
    assert "example.com" not in WebLearner._host_failures
    assert "example.com" not in WebLearner._host_last_failure
