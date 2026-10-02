import json
from types import SimpleNamespace

from my_ai import agent as agent_module
from my_ai import llm as llm_module


def test_ollama_client_preserves_chat_roles_and_history(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": "پاسخ"}}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return Response()

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)
    client = llm_module.OllamaClient()
    result = client.chat("درباره خودت بگو", system="SYSTEM", history=[
        {"role": "user", "content": "سلام"},
        {"role": "assistant", "content": "سلام، من My-AI هستم."},
    ])
    assert result == "پاسخ"
    assert captured["json"]["messages"] == [
        {"role": "system", "content": "SYSTEM"},
        {"role": "user", "content": "سلام"},
        {"role": "assistant", "content": "سلام، من My-AI هستم."},
        {"role": "user", "content": "درباره خودت بگو"},
    ]


def test_ollama_fallback_preserves_system_and_history(monkeypatch):
    captured = []
    primary = "primary-model"
    fallback = "fallback-model"

    class Response:
        def __init__(self, ok): self.ok = ok
        def raise_for_status(self):
            if not self.ok: raise llm_module.httpx.ConnectError("primary down")
        def json(self): return {"message": {"content": "fallback"}}

    def fake_post(url, **kwargs):
        payload = kwargs["json"]
        captured.append(payload)
        return Response(payload["model"] == fallback)

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)
    monkeypatch.setattr(llm_module.OllamaClient, "_preflight_model", lambda self, requested, task: requested)
    monkeypatch.setattr(llm_module.OllamaClient, "_backoff", lambda self, attempt: None)
    monkeypatch.setattr(llm_module.OllamaClient, "_retry_attempts", lambda self: 1)
    client = llm_module.OllamaClient()
    client.model = primary
    client.fallback_chain = [fallback]
    assert client.chat("سؤال", system="SYSTEM", history=[{"role": "user", "content": "قبلی"}]) == "fallback"
    assert captured[0]["messages"] == captured[1]["messages"]
    assert captured[1]["messages"] == [
        {"role": "system", "content": "SYSTEM"},
        {"role": "user", "content": "قبلی"},
        {"role": "user", "content": "سؤال"},
    ]


def test_openai_compatible_client_sends_structured_history(monkeypatch):
    captured = {}
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"output_text": "پاسخ"}
    def fake_post(url, **kwargs):
        captured["url"] = url; captured["json"] = kwargs["json"]; return Response()
    monkeypatch.setattr(llm_module.httpx, "post", fake_post)
    monkeypatch.setattr(llm_module, "settings", SimpleNamespace(openai_api_key="test-key", openai_base_url="http://llm.test/v1", openai_model="test-model", llm_provider="openai"))
    client = llm_module.OpenAICompatibleClient()
    result = client.chat("مدل تو چیست؟", system="IDENTITY", history=[{"role": "user", "content": "سلام"}])
    assert result == "پاسخ"
    assert captured["url"] == "http://llm.test/v1/responses"
    assert captured["json"] == {"model": "test-model", "input": [{"role": "user", "content": "سلام"}, {"role": "user", "content": "مدل تو چیست؟"}], "instructions": "IDENTITY"}


def test_create_llm_auto_prefers_openai_when_key_exists(monkeypatch):
    monkeypatch.setattr(llm_module, "settings", SimpleNamespace(openai_api_key="test-key", openai_base_url="http://llm.test/v1", openai_model="test-model", llm_provider="auto"))
    assert isinstance(llm_module.create_llm(), llm_module.OpenAICompatibleClient)


def test_agent_passes_real_history_and_retrieved_knowledge(monkeypatch):
    captured = {}
    class FakeLLM:
        def chat(self, message, system=None, history=None): captured.update(message=message, system=system, history=history); return "پاسخ درست"
    monkeypatch.setattr(agent_module, "fetch_all", lambda *args: [{"role": "assistant", "content": "قبلی"}, {"role": "user", "content": "سلام"}])
    monkeypatch.setattr(agent_module, "recall", lambda *args: [{"title": "Python", "content": "knowledge"}])
    monkeypatch.setattr(agent_module, "execute", lambda *args: None)
    class FakeRouter:
        def classify(self, message, context=None): return type("Intent", (), {"name": "chat", "args": {"action": "answer"}, "intents": ("chat",)})()
    result = agent_module.Agent(FakeLLM(), router=FakeRouter()).chat("پایتون چیست؟", session_id=7)
    assert result == "پاسخ درست"
    assert captured["history"] == [{"role": "user", "content": "سلام"}, {"role": "assistant", "content": "قبلی"}]
    assert "RELEVANT LOCAL KNOWLEDGE" in captured["system"]
    assert json.dumps({"title": "Python", "content": "knowledge"}, ensure_ascii=False) in captured["system"]
    assert "IDENTITY AND REFERENCE RULES" in captured["system"]


def test_agent_answers_identity_about_itself_not_user(monkeypatch):
    captured = {}
    class FakeLLM:
        model = "test-model"
        def chat(self, *args, **kwargs): captured["called"] = True; return "نباید استفاده شود"
    monkeypatch.setattr(agent_module, "execute", lambda *args: None)
    result = agent_module.Agent(FakeLLM()).chat("درباره خودت بگو", session_id=7)
    assert "My-AI" in result and "test-model" in result and "نباید استفاده شود" not in result
    assert "called" not in captured


def test_openai_compatible_stream_chat(monkeypatch):
    class Response:
        def raise_for_status(self): pass
        def iter_lines(self):
            yield 'data: {"type":"response.output_text.delta","delta":"سلام "}'
            yield 'data: {"type":"response.output_text.delta","delta":"دنیا"}'
            yield 'data: {"type":"response.completed","response":{"usage":{"input_tokens":2,"output_tokens":2}}}'
    class Stream:
        def __enter__(self): return Response()
        def __exit__(self,*args): pass
    monkeypatch.setattr(llm_module.httpx, "stream", lambda *args, **kwargs: Stream())
    monkeypatch.setattr(llm_module, "settings", SimpleNamespace(openai_api_key="test-key",openai_base_url="http://llm.test/v1",openai_model="test-model",offline_strict=False))
    assert list(llm_module.OpenAICompatibleClient().stream_chat("سلام")) == ["سلام ","دنیا"]
