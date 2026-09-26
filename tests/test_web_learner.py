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
