import json

import httpx

from my_ai.infra.llm import OllamaClient


def _response(content, status=200):
    return httpx.Response(status, json={"message": {"content": content}}, request=httpx.Request("POST", "http://127.0.0.1:11434/api/chat"))


def test_structured_chat_uses_multi_stage_fallback_and_preserves_payload(monkeypatch):
    client = OllamaClient.__new__(OllamaClient)
    client.base_url = "http://127.0.0.1:11434"
    client.model = "primary"
    client.fallback_chain = ["fallback-a", "fallback-b"]
    client._options = lambda: {}
    calls = []

    def post(url, **kwargs):
        calls.append(kwargs["json"])
        if kwargs["json"]["model"] != "fallback-b":
            return httpx.Response(503, request=httpx.Request("POST", url))
        return _response(json.dumps({"ok": True}))

    monkeypatch.setattr("my_ai.infra.llm.httpx.post", post)
    result = client.structured_chat_json("keep this context", {"type": "object"}, system="system")
    assert result == {"ok": True}
    assert [item["model"] for item in calls] == ["primary", "primary", "fallback-a", "fallback-a", "fallback-b"]
    assert calls[-1]["messages"][-1]["content"] == "keep this context"
    assert calls[-1]["messages"][0]["content"] == "system"
