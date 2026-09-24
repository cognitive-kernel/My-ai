from pathlib import Path

from my_ai.multimodal import analyze


def test_text_analysis_is_local_and_read_only(tmp_path: Path):
    target = tmp_path / "note.txt"
    target.write_text("hello world", encoding="utf-8")
    result = analyze(str(target))
    assert result["kind"] == "text"
    assert result["content"]["text"] == "hello world"
    assert target.read_text(encoding="utf-8") == "hello world"


def test_unknown_file_gets_safe_generic_analysis(tmp_path: Path):
    target = tmp_path / "data.bin"
    target.write_bytes(b"binary payload")
    result = analyze(str(target))
    assert result["kind"] == "unknown"
    assert result["generic"]["size"] == len(b"binary payload")
    assert "sha256" in result["generic"]


def test_audio_analysis_reports_config_state_without_model(tmp_path: Path, monkeypatch):
    target = tmp_path / "sample.wav"
    target.write_bytes(b"RIFF")
    monkeypatch.delenv("WHISPER_MODEL_PATH", raising=False)
    monkeypatch.setattr("my_ai.multimodal._ffprobe", lambda _path: {"streams": []})
    result = analyze(str(target))
    assert result["kind"] == "audio"
    assert result["transcription"]["status"] == "not_configured"
