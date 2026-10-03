import pytest

pytestmark = pytest.mark.timeout(30)


def test_explicit_quote_request_resolves_market_capability_without_llm():
    from my_ai.domain.router import classify

    class ExplodingClassifier:
        def structured_chat_json(self, *args, **kwargs):
            raise AssertionError("LLM router must not be called for explicit quote capability")

    result = classify("قیمت الان AUD/USD چنده؟", classifier=ExplodingClassifier())
    assert result.name == "chat"
    assert result.requires_confirmation is False
    assert result.args["capability"] == "market.quote"
    assert result.args["symbol"] == "AUDUSD"
    assert result.args["action"] == "answer"
