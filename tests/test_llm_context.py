import json
from types import SimpleNamespace

from my_ai import agent as agent_module
from my_ai import llm as llm_module


def test_ollama_client_preserves_chat_roles_and_history(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": "پاسخ"}}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return Response()

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)
    client = llm_module.OllamaClient()
    result = client.chat(
        "درباره خودت بگو",
        system="SYSTEM",
        history=[
            {"role": "user", "content": "سلام"},
            {"role": "assistant", "content": "سلام، من My-AI هستم."},
        ],
    )

    assert result == "پاسخ"
    assert captured["json"]["messages"] == [
        {"role": "system", "content": "SYSTEM"},
        {"role": "user", "content": "سلام"},
        {"role": "assistant", "content": "سلام، من My-AI هستم."},
        {"role": "user", "content": "درباره خودت بگو"},
    ]


def test_openai_compatible_client_sends_structured_history(monkeypatch):
    captured = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"output_text": "پاسخ"}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return Response()

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)
    monkeypatch.setattr(
        llm_module,
        "settings",
        SimpleNamespace(
            openai_api_key="test-key",
            openai_base_url="http://llm.test/v1",
            openai_model="test-model",
            llm_provider="openai",
        ),
    )
    client = llm_module.OpenAICompatibleClient()
    result = client.chat(
        "مدل تو چیست؟",
        system="IDENTITY",
        history=[{"role": "user", "content": "سلام"}],
    )

    assert result == "پاسخ"
    assert captured["url"] == "http://llm.test/v1/responses"
    assert captured["json"] == {
        "model": "test-model",
        "input": [
            {"role": "user", "content": "سلام"},
            {"role": "user", "content": "مدل تو چیست؟"},
        ],
        "instructions": "IDENTITY",
    }


def test_create_llm_auto_prefers_openai_when_key_exists(monkeypatch):
    monkeypatch.setattr(
        llm_module,
        "settings",
        SimpleNamespace(
            openai_api_key="test-key",
            openai_base_url="http://llm.test/v1",
            openai_model="test-model",
            llm_provider="auto",
        ),
    )
    assert isinstance(llm_module.create_llm(), llm_module.OllamaClient)


def test_agent_passes_real_history_and_retrieved_knowledge(monkeypatch):
    captured = {}

    class FakeLLM:
        def chat(self, message, system=None, history=None):
            captured["message"] = message
            captured["system"] = system
            captured["history"] = history
            return "پاسخ درست"

    # Agent queries the database newest-first, then restores chronological order.
    monkeypatch.setattr(agent_module, "fetch_all", lambda *args: [
        {"role": "assistant", "content": "قبلی"},
        {"role": "user", "content": "سلام"},
    ])
    monkeypatch.setattr(agent_module, "recall", lambda *args: [{"title": "Python", "content": "knowledge"}])
    monkeypatch.setattr(agent_module, "execute", lambda *args: None)
    agent = agent_module.Agent(FakeLLM())

    result = agent.chat("پایتون چیست؟", session_id=7)

    assert result == "پاسخ درست"
    assert captured["message"] == "پایتون چیست؟"
    assert captured["history"] == [
        {"role": "user", "content": "سلام"},
        {"role": "assistant", "content": "قبلی"},
    ]
    assert "RELEVANT LOCAL KNOWLEDGE" in captured["system"]
    assert json.dumps({"title": "Python", "content": "knowledge"}, ensure_ascii=False) in captured["system"]
    assert "IDENTITY AND REFERENCE RULES" in captured["system"]


def test_agent_answers_identity_about_itself_not_user(monkeypatch):
    captured = {}

    class FakeLLM:
        model = "test-model"

        def chat(self, *args, **kwargs):
            captured["called"] = True
            return "نباید استفاده شود"

    monkeypatch.setattr(agent_module, "execute", lambda *args: None)
    agent = agent_module.Agent(FakeLLM())

    result = agent.chat("درباره خودت بگو", session_id=7)

    assert "My-AI" in result
    assert "test-model" in result
    assert "نباید استفاده شود" not in result
    assert "called" not in captured
