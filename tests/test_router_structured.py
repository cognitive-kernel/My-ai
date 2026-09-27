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
