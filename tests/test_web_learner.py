import pytest

from my_ai.web_learner import WebLearner


def test_web_learner_rejects_invalid_scheme():
    with pytest.raises(ValueError):
        WebLearner().fetch("file:///tmp/test.txt")
