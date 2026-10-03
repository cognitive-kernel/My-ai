from pathlib import Path


def test_chat_ui_uses_persian_calendar_datetime():
    html = Path("my_ai/static/index.html").read_text(encoding="utf-8")
    assert "fa-IR-u-ca-persian" in html
    assert "year:'numeric'" in html
    assert "second:'2-digit'" in html


def test_first_message_creates_a_new_server_session_and_continuation_reuses_it():
    html = Path("my_ai/static/index.html").read_text(encoding="utf-8")
    assert "if(currentSessionId===null){var created=await post('/chat/sessions',{message:m});currentSessionId=created.id;}" in html
    assert "post('/chat',{message:m,session_id:currentSessionId,attachments:uploaded})" in html


def test_new_chat_clears_only_the_active_view_without_deleting_history():
    html = Path("my_ai/static/index.html").read_text(encoding="utf-8")
    assert "async function newChat(){currentSessionId=null;newChatPending=true;renderHistory([]);await loadSessions(false)" in html
    assert "if(autoSelect&&currentSessionId===null&&list.length)await selectChat(Number(list[0].id))" in html
    assert "if(j.session_id)currentSessionId=j.session_id;newChatPending=false;await loadSessions(false);" in html


def test_server_history_is_persistent_across_page_reload():
    api = Path("my_ai/api.py").read_text(encoding="utf-8")
    html = Path("my_ai/static/index.html").read_text(encoding="utf-8")
    assert 'SELECT c.id,c.role,c.content,c.created_at FROM conversations' in api
    assert "fetch('/chat/history?session_id=" in html
    assert "if(currentSessionId===null&&list.length)await selectChat(Number(list[0].id))" in html


def test_new_chat_does_not_auto_select_an_existing_recent_chat():
    html = Path("my_ai/static/index.html").read_text(encoding="utf-8")
    assert "await loadSessions(false)" in html
    assert "async function selectChat(id){try{newChatPending=false;currentSessionId=Number(id);" in html
    assert "var recognition=null,voiceLocale='fa-IR',uiLang='fa',busy=false,currentSessionId=null,pendingFiles=[],newChatPending=false;" in html
