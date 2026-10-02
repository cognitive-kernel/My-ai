import json

from my_ai.infra.router_llm import OpenAIStructuredRouterClient


def test_openai_router_uses_strict_responses_json_schema(monkeypatch):
    calls = []

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"output_text": json.dumps({"primary": "chat"})}

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr("my_ai.infra.router_llm.httpx.post", fake_post)
    client = OpenAIStructuredRouterClient.__new__(OpenAIStructuredRouterClient)
    client.base_url = "https://api.example.test/v1"
    client.model = "router-model"
    client.api_key = "test-key"
    client.provider_name = "openai-router"
    result = client.structured_chat_json("hello", {"type": "object"}, "system")
    assert result["primary"] == "chat"
    payload = calls[0][1]["json"]
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True
    assert payload["text"]["format"]["schema"] == {"type": "object"}
