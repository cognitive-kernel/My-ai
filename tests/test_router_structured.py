from my_ai.router import classify, _parse_router_payload

def test_router_schema_rejects_missing_fields():
    try:
        _parse_router_payload('{"primary":"chat"}')
    except ValueError:
        return
    raise AssertionError("missing structured fields must be rejected")

def test_router_fallback_handles_farsi_learning():
    intent = classify("لطفاً درباره پایتون به من آموزش بده")
    assert intent.name in {"learning", "chat"}
    assert 0 <= intent.confidence <= 1


def test_structured_router_handles_ambiguous_multi_intent(monkeypatch):
    import my_ai.domain.router as router
    class Client:
        def structured_chat_json(self, prompt, schema, system=None):
            return {"primary": "learning", "intents": ["learning", "coding"], "confidence": 0.91,
                    "language": "fa", "topic": "Python", "goal": "learn then implement"}
    monkeypatch.setattr(router, "create_llm", lambda task: Client(), raising=False)
    monkeypatch.setattr(router.settings, "router_llm_enabled", True, raising=False)
    # _llm_classify accepts the client directly in the current implementation.
    result = router._llm_classify("پایتون را یاد بگیر و بعد یک مثال بنویس", Client())
    assert result is not None
    assert result.intents == ("learning", "coding")
    assert result.confidence == 0.91
