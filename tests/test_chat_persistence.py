from my_ai.agent_runtime import Agent, PreparedChat


class _FakeLLM:
    def stream_chat(self, *args, **kwargs):
        yield "first"
        yield " second"


def test_stream_chat_persists_user_before_processing_and_reply_incrementally(monkeypatch):
    events = []
    next_id = iter([101, 102])

    def fake_execute(sql, params=()):
        events.append((sql, params))
        if sql.startswith("INSERT INTO conversations"):
            return next(next_id)
        return None

    monkeypatch.setattr("my_ai.agent_runtime.execute", fake_execute)
    agent = Agent()

    def prepare(message, session_id, attachments=None, intent=None):
        assert events[0][0].startswith("INSERT INTO conversations")
        assert events[0][1] == (session_id, "user", message)
        return PreparedChat(
            message=message,
            session_id=session_id,
            attachments=[],
            history=[],
            context="",
            conversation_state={},
            llm=_FakeLLM(),
            llm_message=message,
            system="",
        )

    monkeypatch.setattr(agent, "_prepare_chat_context", prepare)
    monkeypatch.setattr(agent, "_handle_unknown", lambda answer, *_: answer)
    monkeypatch.setattr(agent, "_update_state", lambda *_: None)

    stream = agent.stream_chat("hello", session_id=7)
    assert next(stream) == "first"
    assert any(sql.startswith("UPDATE conversations SET content=? WHERE id=?") and params == ("first", 102) for sql, params in events)
    assert next(stream) == " second"
    assert any(sql.startswith("UPDATE conversations SET content=? WHERE id=?") and params == ("first second", 102) for sql, params in events)

    try:
        next(stream)
    except StopIteration:
        pass
    else:
        raise AssertionError("stream should be exhausted")
