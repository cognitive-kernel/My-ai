import httpx
import pytest

from my_ai.infra import llm as llm_module


def test_ollama_chat_retry_is_bounded(monkeypatch):
    calls = []
    class Settings:
        ollama_base_url = "http://127.0.0.1:11434"
        ollama_model = "primary"
        fallback_model = "fallback"
        coding_model = "primary"
        routing_model = "primary"
        ollama_num_ctx = 128
        ollama_keep_alive = "0"
        offline_strict = True
        llm_retry_attempts = 2
        llm_retry_backoff_seconds = 0
        llm_timeout_seconds = 1
        resource_wait_seconds = 0
    monkeypatch.setattr(llm_module, "_settings", lambda: Settings())
    monkeypatch.setattr(llm_module.OllamaClient, "_preflight_model", lambda self, requested, task: requested)
    client = llm_module.OllamaClient()
    client.fallback_chain = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise httpx.ConnectError("offline")
    monkeypatch.setattr(llm_module.httpx, "post", fail)
    monkeypatch.setattr(llm_module, "wait_until_available", lambda *a, **k: None)

    with pytest.raises(llm_module.LLMError):
        client.chat("hello")
    assert len(calls) == 2


def test_stream_preserves_context_when_falling_back(monkeypatch):
    class Settings:
        ollama_base_url = "http://127.0.0.1:11434"
        ollama_model = "primary"
        fallback_model = "fallback"
        coding_model = "primary"
        routing_model = "primary"
        ollama_num_ctx = 128
        ollama_keep_alive = "0"
        offline_strict = True
        llm_retry_attempts = 1
        llm_retry_backoff_seconds = 0
        llm_timeout_seconds = 1
        resource_wait_seconds = 0
    monkeypatch.setattr(llm_module, "_settings", lambda: Settings())
    monkeypatch.setattr(llm_module.OllamaClient, "_preflight_model", lambda self, requested, task: requested)
    monkeypatch.setattr(llm_module, "wait_until_available", lambda *a, **k: None)
    client = llm_module.OllamaClient()
    client.fallback_chain = ["fallback"]
    seen = []

    class Response:
        def raise_for_status(self):
            return None
        def iter_lines(self):
            yield '{"message":{"content":"ok"},"done":true}'

    class Stream:
        def __init__(self, *args, **kwargs):
            seen.append(kwargs["json"])
        def __enter__(self): return Response()
        def __exit__(self, *args): return False

    def stream(method, url, **kwargs):
        if kwargs["json"]["model"] == "primary":
            raise httpx.ConnectError("primary down")
        return Stream(method, url, **kwargs)

    monkeypatch.setattr(llm_module.httpx, "stream", stream)
    result = "".join(client.stream_chat("question", system="system", history=[{"role":"assistant","content":"context"}]))
    assert result == "ok"
    assert seen[0]["messages"][-2:] == [{"role":"assistant","content":"context"},{"role":"user","content":"question"}]
