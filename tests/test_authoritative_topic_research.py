from my_ai.learner import LearningEngine


def test_authoritative_topic_reference_discovery_uses_configured_search_policy():
    engine = LearningEngine.__new__(LearningEngine)

    class FakeWeb:
        def search(self, query, domains=None, limit=6):
            assert query == "Python asyncio"
            assert domains == ["docs.python.org"]
            assert limit == 3
            return [{"title": "Python docs", "url": "https://docs.python.org/3/library/asyncio.html"}]

    engine.web = FakeWeb()
    result = engine.find_authoritative_references("Python asyncio", ["docs.python.org"], 3)
    assert result["topic"] == "Python asyncio"
    assert result["count"] == 1
    assert result["sources"][0]["url"].startswith("https://docs.python.org/")


def test_authoritative_topic_reference_requires_topic():
    engine = LearningEngine.__new__(LearningEngine)
    engine.web = object()
    try:
        engine.find_authoritative_references(" ")
    except ValueError as exc:
        assert str(exc) == "Topic is required."
    else:
        raise AssertionError("expected ValueError")
