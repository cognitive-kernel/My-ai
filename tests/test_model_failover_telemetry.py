import httpx
from my_ai.infra import llm as llm_module
from my_ai.metrics import snapshot

def test_multi_stage_fallback_and_context_preservation(monkeypatch):
    class Settings:
        ollama_base_url="http://127.0.0.1:11434"
        ollama_model="primary"
        fallback_model="fallback1"
        coding_model="fallback2"
        routing_model="fallback3"
        ollama_num_ctx=128
        ollama_keep_alive="0"
        offline_strict=True
        llm_retry_attempts=1
        llm_retry_backoff_seconds=0
        llm_timeout_seconds=1
        resource_wait_seconds=0
    monkeypatch.setattr(llm_module, "_settings", lambda: Settings())
    monkeypatch.setattr(llm_module.ModelManager, "fallback_chain", lambda self, requested: ["fallback1", "fallback2"])
    monkeypatch.setattr(llm_module.OllamaClient, "_preflight_model", lambda self, requested, task: requested)
    monkeypatch.setattr(llm_module, "wait_until_available", lambda *a, **k: None)
    client=llm_module.OllamaClient()
    seen=[]
    def fail_or_success(url, **kwargs):
        model=kwargs["json"]["model"]; seen.append((model, kwargs["json"]["messages"]))
        if model != "fallback2":
            raise httpx.ConnectError(model)
        return type("R", (), {"raise_for_status": lambda self: None, "json": lambda self: {"message":{"content":"ok"}}})()
    monkeypatch.setattr(llm_module.httpx, "post", fail_or_success)
    assert client.chat("current question", history=[{"role":"assistant","content":"prior context"}])=="ok"
    assert [model for model, _ in seen] == ["primary","fallback1","fallback2"]
    assert all(messages[-2]["content"]=="prior context" for _, messages in seen)
    routing=snapshot()["routing"]
    assert any("failure_attempt_1" in key for key in routing)
