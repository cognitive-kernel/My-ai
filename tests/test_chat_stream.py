from my_ai import agent as agent_module


class FakeLLM:
    def stream_chat(self, message, system=None, history=None):
        assert "My-AI" in system
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
    conversation_writes = [item for item in writes if len(item) >= 2 and isinstance(item[1], tuple)]
    assert conversation_writes[0][1] == (7, "user", "سلام")
    assert conversation_writes[1][1] == (7, "assistant", "سلام دنیا")


def test_stream_reconnect_reuses_persisted_session_context(monkeypatch):
    writes = []
    stored = []
    def fetch(sql, params=()):
        if "FROM conversations" in sql:
            return list(stored)
        return []
    def execute(sql, params=()):
        writes.append((sql, params))
        if "INSERT INTO conversations" in sql:
            stored.append({"role": params[1], "content": params[2]})
        return 1
    monkeypatch.setattr(agent_module, "fetch_all", fetch)
    monkeypatch.setattr(agent_module, "recall", lambda *args, **kwargs: [])
    monkeypatch.setattr(agent_module, "recent_lessons", lambda *args, **kwargs: [])
    monkeypatch.setattr(agent_module, "execute", execute)
    seen = []
    class ContextLLM:
        def stream_chat(self, message, system=None, history=None):
            seen.append(list(history or []))
            yield "reply"
    class FakeRouter:
        def classify(self, message, context=None):
            return type("Intent", (), {"name": "chat", "args": {"action": "answer"}, "intents": ("chat",)})()
    agent = agent_module.Agent(llm=ContextLLM(), router=FakeRouter())
    list(agent.stream_chat("first", session_id=9))
    list(agent.stream_chat("second", session_id=9))
    assert seen[0] == []
    assert seen[1] == [{"role": "user", "content": "first"}, {"role": "assistant", "content": "reply"}]
