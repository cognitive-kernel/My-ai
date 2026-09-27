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
