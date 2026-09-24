from pathlib import Path

from my_ai.multimodal import analyze


def test_text_analysis_is_local_and_read_only(tmp_path: Path):
    target = tmp_path / "note.txt"
    target.write_text("hello world", encoding="utf-8")
    result = analyze(str(target))
    assert result["kind"] == "text"
    assert result["content"]["text"] == "hello world"
    assert target.read_text(encoding="utf-8") == "hello world"
