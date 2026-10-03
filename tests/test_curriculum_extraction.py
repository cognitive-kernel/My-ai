from types import SimpleNamespace

from my_ai import settings_feature as sf


def test_extract_curriculum_persists_source_backed_topics(monkeypatch):
    sf._setup()
    monkeypatch.setattr(sf, "require_admin", lambda request: {"id": 1})
    
    class FakeWeb:
        def fetch(self, url):
            return ("Reference", "Fundamentals\nAdvanced usage")

    class FakeLLM:
        def chat(self, prompt, system=None):
            return '{"topics":[{"title":"Fundamentals","goal":"Learn basics","source_url":"https://example.com/course"},{"title":"Advanced","goal":"Apply concepts","source_url":"https://example.com/course"}]}'

    monkeypatch.setattr(sf, "WebLearner", FakeWeb, raising=False)
    monkeypatch.setattr(sf, "create_llm", lambda model: FakeLLM())
    request = sf.CurriculumExtractRequest(
        name="Extracted Curriculum",
        sources=["https://example.com/course"],
    )
    result = sf.extract_curriculum(request, SimpleNamespace())
    rows = sf.fetch_all(
        "SELECT title,goal,source_url FROM custom_course_topics WHERE course_id=? ORDER BY topic_order",
        (result["id"],),
    )
    assert result["status"] == "created"
    assert [x["title"] for x in rows] == ["Fundamentals", "Advanced"]
    assert all(x["source_url"] == "https://example.com/course" for x in rows)


def test_extract_curriculum_rejects_model_urls_outside_supplied_sources(monkeypatch):
    sf._setup()
    monkeypatch.setattr(sf, "require_admin", lambda request: {"id": 1})

    class FakeWeb:
        def fetch(self, url):
            return ("Reference", "content")

    class FakeLLM:
        def chat(self, prompt, system=None):
            return '{"topics":[{"title":"Topic","goal":"Goal","source_url":"https://evil.example"}]}'

    monkeypatch.setattr(sf, "WebLearner", FakeWeb, raising=False)
    monkeypatch.setattr(sf, "create_llm", lambda model: FakeLLM())
    request = sf.CurriculumExtractRequest(
        name="Source Validation Curriculum",
        sources=["https://example.com/course"],
    )
    result = sf.extract_curriculum(request, SimpleNamespace())
    row = sf.fetch_all(
        "SELECT source_url FROM custom_course_topics WHERE course_id=?",
        (result["id"],),
    )[0]
    assert row["source_url"] is None
