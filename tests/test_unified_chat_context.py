from my_ai import agent as agent_module


class Intent:
    name = "general"
    args = {"action": "answer"}


class FakeLLM:
    def __init__(self):
        self.calls = []

    def chat(self, message, system=None, history=None):
        self.calls.append((message, system, history))
        return "answer"

    def stream_chat(self, message, system=None, history=None):
        self.calls.append((message, system, history))
        yield "answer"


def _patch_common(monkeypatch):
    monkeypatch.setattr(agent_module, "fetch_all", lambda *a, **k: [])
    monkeypatch.setattr(agent_module, "recall", lambda *a, **k: [])
    monkeypatch.setattr(agent_module, "recent_lessons", lambda *a, **k: [])
    monkeypatch.setattr(agent_module, "execute", lambda *a, **k: None)
    monkeypatch.setattr(agent_module.Agent, "_classify", lambda self, *a, **k: Intent())


def test_chat_and_stream_share_preparation_order(monkeypatch):
    _patch_common(monkeypatch)
    events = []
    monkeypatch.setattr(agent_module.Agent, "_web_learning_confirmation", lambda self, *a: events.append("web") or None)
    monkeypatch.setattr(agent_module.Agent, "_semantic_maintenance", lambda self, *a: events.append("maintenance") or None)
        agent = agent_module.Agent(llm=FakeLLM())
    list(agent.stream_chat("hello", 1, attachments=[]))
    assert events == ["web", "maintenance"]


def test_stream_uses_attachments_and_emits_citations_before_model(monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(agent_module, "recall", lambda *a, **k: [{"id": 7, "title": "T", "source_url": "local://t", "confidence": 0.9, "confidence_calibrated": True}])
    monkeypatch.setattr(agent_module.Agent, "_attachment_context", lambda self, items: "ATTACHMENT-CONTEXT" if items else "")
    llm = FakeLLM()
    agent = agent_module.Agent(llm=llm)
    chunks = list(agent.stream_chat("hello", 2, attachments=[{"path": "/tmp/a.txt", "name": "a.txt"}]))
    assert chunks[0].startswith("Sources (mandatory provenance):")
    assert "[K7]" in chunks[0]
    assert llm.calls[0][0].endswith("ATTACHMENT-CONTEXT")
