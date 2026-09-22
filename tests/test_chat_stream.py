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
    agent = agent_module.Agent(llm=FakeLLM())
    chunks = list(agent.stream_chat("سلام", session_id=7))
    assert "".join(chunks) == "سلام دنیا"
    assert writes[0][1] == (7, "user", "سلام")
    assert writes[1][1] == (7, "assistant", "سلام دنیا")
