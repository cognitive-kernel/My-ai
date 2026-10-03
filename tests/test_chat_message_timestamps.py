from pathlib import Path


def test_chat_ui_renders_question_and_answer_times():
    html = Path("my_ai/static/index.html").read_text(encoding="utf-8")
    assert "function formatMessageTime(" in html
    assert "زمان پرسش:" in html
    assert "زمان پاسخ:" in html
    assert "new Date().toISOString()" in html
    assert "x.created_at" in html
