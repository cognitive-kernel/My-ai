from my_ai import agent as agent_module


class FakeLLM:
    def stream_chat(self, message, system=None, history=None):
        assert "My-AI" in system
        assert history == []
        yield "سلام "
        yield "دنیا"


def test_agent_stream_chat_persists_context(monkeypatch):
    writes = []
    monkeypatch.setattr(agent_module, "fetch_all", lambda *args, **kwargs: [])
    monkeypatch.setattr(agent_module, "recall", lambda *args, **kwargs: [])
    monkeypatch.setattr(agent_module, "recent_lessons", lambda *args, **kwargs: [])
    monkeypatch.setattr(agent_module, "execute", lambda *args: writes.append(args))
    class FakeRouter:
        def classify(self, message, context=None):
            return type("Intent", (), {"name": "chat", "args": {"action": "answer"}, "intents": ("chat",)})()
    agent = agent_module.Agent(llm=FakeLLM(), router=FakeRouter())
    chunks = list(agent.stream_chat("سلام", session_id=7))
    assert "".join(chunks) == "سلام دنیا"
    conversation_writes = [
        item for item in writes
        if len(item) >= 2
        and isinstance(item[1], tuple)
        and item[0].startswith("INSERT INTO conversations")
    ]
    assert conversation_writes[0][1] == (7, "user", "سلام")
    assert conversation_writes[1][1][0:2] == (7, "assistant")
    assistant_insert_content = conversation_writes[1][1][2]
    assistant_updates = [
        item for item in writes
        if len(item) >= 2
        and isinstance(item[1], tuple)
        and item[0].startswith("UPDATE conversations SET content=? WHERE id=?")
    ]
    if assistant_insert_content == "":
        assert assistant_updates
        assert any(item[1][0] == "سلام دنیا" for item in assistant_updates)
    else:
        assert assistant_insert_content == "سلام دنیا"
