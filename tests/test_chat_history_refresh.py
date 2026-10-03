from pathlib import Path


def test_chat_history_is_restored_from_server_after_refresh():
    html = Path("my_ai/static/index.html").read_text(encoding="utf-8")
    assert "fetch('/chat/history?session_id=" in html
    assert "if(currentSessionId===null&&list.length)await selectChat(Number(list[0].id))" in html
    assert "await loadSessions();" in html
    assert "renderHistory(j.messages||[],j.attachments||[])" in html


def test_chat_history_endpoint_exposes_persisted_created_at():
    api = Path("my_ai/api.py").read_text(encoding="utf-8")
    assert 'SELECT c.id,c.role,c.content,c.created_at FROM conversations' in api
    assert 'return {"messages":rows,"attachments":attachments}' in api
