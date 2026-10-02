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


def test_model_inference_policy_is_independent_from_legacy_llm_policy(monkeypatch):
    class Settings:
        llm_retry_attempts = 5
        llm_retry_backoff_seconds = 9
        llm_timeout_seconds = 99
        llm_model_retry_attempts = 1
        llm_model_retry_backoff_seconds = 0
        llm_model_timeout_seconds = 2
    monkeypatch.setattr(llm_module, "_settings", lambda: Settings())
    client = llm_module.OllamaClient.__new__(llm_module.OllamaClient)
    assert client._retry_attempts() == 1
    assert client._timeout() == 2
    client._backoff(1)


def test_registered_llm_policy_overrides_environment_defaults(monkeypatch):
    class Settings:
        llm_retry_attempts = 5
        llm_retry_backoff_seconds = 9
        llm_timeout_seconds = 99
        llm_model_retry_attempts = 5
        llm_model_timeout_seconds = 99
    values = {"llm.retry_attempts": "1", "llm.timeout_seconds": "2"}
    monkeypatch.setattr(llm_module, "_settings", lambda: Settings())
    monkeypatch.setattr(llm_module, "get_setting", lambda key, default=None: values.get(key, default))
    client = llm_module.OllamaClient.__new__(llm_module.OllamaClient)
    assert client._retry_attempts() == 1
    assert client._timeout() == 2


def test_custom_provider_uses_registry_configuration(monkeypatch):
    import my_ai.infra.llm as module
    class Settings:
        llm_provider = "ollama"
        offline_strict = False
        openai_base_url = "http://default"
        openai_model = "default"
        openai_api_key = "default-key"
    values = {"llm.provider": "custom-openai-compatible", "llm.custom.base_url": "http://custom", "llm.custom.model": "custom-model", "llm.custom.api_key": "custom-key"}
    monkeypatch.setattr(module, "_settings", lambda: Settings())
    monkeypatch.setattr(module, "get_setting", lambda key, default=None: values.get(key, default))
    client = module.create_llm()
    assert client.base_url == "http://custom"
    assert client.model == "custom-model"
    assert client.api_key == "custom-key"
    assert client.provider_name == "custom-openai-compatible"


def test_custom_provider_missing_endpoint_is_rejected(monkeypatch):
    import my_ai.infra.llm as module
    class Settings:
        llm_provider = "ollama"
        offline_strict = False
        openai_base_url = "http://default"
        openai_model = "default"
        openai_api_key = "default-key"
    values = {"llm.provider": "custom-openai-compatible", "llm.custom.base_url": "", "llm.custom.model": "custom-model", "llm.custom.api_key": "custom-key"}
    monkeypatch.setattr(module, "_settings", lambda: Settings())
    monkeypatch.setattr(module, "get_setting", lambda key, default=None: values.get(key, default))
    try:
        module.create_llm()
    except module.LLMError as exc:
        assert "base URL" in str(exc)
    else:
        raise AssertionError("Expected custom provider configuration error")
