from my_ai.config import settings
from my_ai.llm import OllamaClient


def test_ollama_task_routing():
    assert OllamaClient("coding").model == settings.coding_model
    assert OllamaClient("patch").model == settings.coding_model
    assert OllamaClient("routing").model == settings.routing_model
    assert OllamaClient("classify").model == settings.routing_model
    assert OllamaClient("general").model == settings.ollama_model

def test_preflight_uses_fallback_when_requested_model_is_missing(monkeypatch):
    import httpx
    from my_ai.llm import OllamaClient
    monkeypatch.setattr("my_ai.infra.llm.httpx.get", lambda *args, **kwargs: httpx.Response(200, json={"models":[{"name":settings.fallback_model}]}, request=httpx.Request("GET","http://127.0.0.1:11434/api/tags")))
    client = OllamaClient("coding")
    if settings.coding_model != settings.fallback_model:
        assert client.model == settings.fallback_model
        assert client.route_reason == "preflight_fallback"


def test_preflight_keeps_requested_model_when_available(monkeypatch):
    import httpx
    from my_ai.llm import OllamaClient
    monkeypatch.setattr("my_ai.infra.llm.httpx.get", lambda *args, **kwargs: httpx.Response(200, json={"models":[{"name":settings.coding_model}]}, request=httpx.Request("GET","http://127.0.0.1:11434/api/tags")))
    client = OllamaClient("coding")
    assert client.model == settings.coding_model
