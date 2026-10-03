from pathlib import Path

INDEX = Path(__file__).parents[1] / "my_ai" / "static" / "index.html"


def test_chat_ui_has_fenced_code_card_contract():
    text = INDEX.read_text(encoding="utf-8")
    assert "function codeBlocks(text)" in text
    assert "/```([a-zA-Z0-9_+.#-]*)\\r?\\n([\\s\\S]*?)```/g" in text
    assert "function renderMessageText" in text
    assert "کپی کد" in text
    assert "navigator.clipboard.writeText" in text


def test_chat_ui_supports_multiple_pending_files():
    text = INDEX.read_text(encoding="utf-8")
    assert "pendingFiles" in text
    assert "addFileCards" in text
    assert "uploadPendingFiles" in text

def test_chat_ui_has_global_navigation():
    text = INDEX.read_text(encoding="utf-8")
    assert 'id=' + chr(39) + 'myAiGlobalNav' + chr(39) in text
    assert "href='/learning'" in text
    assert "href='/image'" in text
    assert "href='/settings'" in text
    assert "href='/settings/sections'" not in text
    assert "href='/self-diagnostics'" in text
    assert "href='/help#chat'" in text
