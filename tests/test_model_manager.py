import httpx

from my_ai.config import settings
from my_ai.model_manager import ModelManager


def _tags(names):
    return httpx.Response(200, json={"models": [{"name": name} for name in names]}, request=httpx.Request("GET", "http://127.0.0.1:11434/api/tags"))


def test_model_inventory_contains_all_configured_roles():
    roles = {item["role"] for item in ModelManager().inventory()}
    assert {"general", "routing", "coding", "fallback", "embedding"}.issubset(roles)


def test_model_health_reports_available_and_unavailable(monkeypatch):
    monkeypatch.setattr("my_ai.model_manager.httpx.get", lambda *a, **k: _tags([settings.ollama_model]))
    manager = ModelManager()
    assert manager.health(settings.ollama_model).available is True
    assert manager.health("definitely-missing-model").available is False


def test_model_health_reports_provider_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr("my_ai.model_manager.httpx.get", fail)
    status = ModelManager().health(settings.ollama_model)
    assert status.available is False
    assert status.error == "offline"


def test_choose_fallback_only_when_fallback_is_available(monkeypatch):
    monkeypatch.setattr("my_ai.model_manager.httpx.get", lambda *a, **k: _tags([settings.fallback_model]))
    manager = ModelManager()
    assert manager.choose_fallback("missing-primary") == settings.fallback_model


def test_fallback_chain_is_ordered_and_unique(monkeypatch):
    names = [settings.fallback_model, settings.coding_model, settings.routing_model]
    monkeypatch.setattr("my_ai.model_manager.httpx.get", lambda *a, **k: _tags(names))
    manager = ModelManager()
    chain = manager.fallback_chain("primary")
    assert chain
    assert chain == list(dict.fromkeys(chain))
    assert all(name in names for name in chain)


def test_route_snapshot_exposes_failure_and_fallback(monkeypatch):
    monkeypatch.setattr("my_ai.model_manager.httpx.get", lambda *a, **k: _tags([settings.fallback_model]))
    manager = ModelManager()
    snapshot = manager.route_snapshot("primary")
    assert snapshot["requested_available"] is False
    assert settings.fallback_model in snapshot["fallback_chain"]


def test_ollama_client_uses_central_health_manager(monkeypatch):
    monkeypatch.setattr("my_ai.model_manager.httpx.get", lambda *a, **k: _tags([settings.fallback_model]))
    from my_ai.llm import OllamaClient
    client = OllamaClient("coding")
    if settings.coding_model != settings.fallback_model:
        assert client.model == settings.fallback_model
        assert client.route_reason == "preflight_fallback"


def test_ollama_chat_retries_then_succeeds_without_fallback(monkeypatch):
    from my_ai import llm as llm_module
    calls = []

    class Response:
        def __init__(self, ok): self.ok = ok
        def raise_for_status(self):
            if not self.ok: raise httpx.ConnectError("temporary")
        def json(self): return {"message": {"content": "OK"}}

    def fake_post(url, **kwargs):
        calls.append(kwargs["json"]["model"])
        return Response(len(calls) >= 2)

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)
    monkeypatch.setattr(llm_module.OllamaClient, "_preflight_model", lambda self, requested, task: requested)
    monkeypatch.setattr(llm_module.OllamaClient, "_backoff", lambda self, attempt: None)
    monkeypatch.setattr(llm_module.OllamaClient, "_retry_attempts", lambda self: 2)
    client = llm_module.OllamaClient()
    assert client.chat("hello") == "OK"
    assert len(calls) == 2
    assert calls[0] == calls[1] == client.default_model


def test_ollama_chat_uses_second_fallback_after_retry_exhaustion(monkeypatch):
    from my_ai import llm as llm_module
    calls = []
    primary = settings.ollama_model
    fallback = "fallback-test-model"

    class Response:
        def __init__(self, model): self.model = model
        def raise_for_status(self):
            if self.model == primary: raise httpx.ConnectError("primary down")
        def json(self): return {"message": {"content": "fallback-ok"}}

    def fake_post(url, **kwargs):
        model = kwargs["json"]["model"]; calls.append(model); return Response(model)

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)
    monkeypatch.setattr(llm_module.OllamaClient, "_preflight_model", lambda self, requested, task: requested)
    monkeypatch.setattr(llm_module.OllamaClient, "_backoff", lambda self, attempt: None)
    monkeypatch.setattr(llm_module.OllamaClient, "_retry_attempts", lambda self: 2)
    client = llm_module.OllamaClient()
    client.fallback_chain = [fallback]
    assert client.chat("hello") == "fallback-ok"
    assert calls[:2] == [primary, primary]
    assert calls[2] == fallback
    assert client.model == fallback
