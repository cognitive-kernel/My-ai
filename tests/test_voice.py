import pytest


def test_voice_does_not_fallback_to_arbitrary_main(monkeypatch):
    import my_ai.voice as voice
    monkeypatch.setattr(voice.shutil, "which", lambda name: "/tmp/main" if name == "main" else None)
    assert voice._whisper_binary() is None


def test_voice_uses_configured_binary(monkeypatch, tmp_path):
    import my_ai.voice as voice
    binary=tmp_path / "whisper-cli"
    binary.write_text("binary")
    binary.chmod(0o755)
    monkeypatch.setenv("WHISPER_CPP_BIN", str(binary))
    assert voice._whisper_binary() == str(binary.resolve())


def test_offline_roundtrip_composes_stt_and_tts(monkeypatch, tmp_path):
    import my_ai.voice as voice
    monkeypatch.setattr(voice, "transcribe", lambda *args, **kwargs: "سلام")
    monkeypatch.setattr(voice, "synthesize", lambda text, model, output: str(output))
    result = voice.offline_roundtrip("audio.wav", "whisper.bin", "piper.onnx", str(tmp_path / "out.wav"))
    assert result["text"] == "سلام"
    assert result["audio_path"].endswith("out.wav")


def test_voice_status_uses_configured_local_models(monkeypatch, tmp_path):
    import my_ai.voice as voice
    whisper = tmp_path / "whisper.bin"
    piper = tmp_path / "piper.onnx"
    whisper.write_text("model")
    piper.write_text("model")
    monkeypatch.setenv("WHISPER_MODEL_PATH", str(whisper))
    monkeypatch.setenv("PIPER_MODEL_PATH", str(piper))
    monkeypatch.setattr(voice, "_whisper_binary", lambda: "whisper-cli")
    monkeypatch.setattr(voice, "_piper_binary", lambda: "piper")
    monkeypatch.setattr(voice.subprocess, "run", lambda *args, **kwargs: type("R", (), {"returncode": 0})())
    result = voice.status()
    assert result["offline_ready"] is True


def test_transcribe_rejects_missing_audio_or_model(monkeypatch, tmp_path):
    import my_ai.voice as voice
    binary = tmp_path / "whisper-cli"
    binary.write_text("binary")
    binary.chmod(0o755)
    monkeypatch.setenv("WHISPER_CPP_BIN", str(binary))
    import pytest
    with pytest.raises(FileNotFoundError):
        voice.transcribe(str(tmp_path / "missing.wav"), str(tmp_path / "missing.bin"))


def test_synthesize_rejects_missing_piper_model(monkeypatch, tmp_path):
    import my_ai.voice as voice
    monkeypatch.setattr(voice, "_piper_binary", lambda: "/usr/bin/piper")
    import pytest
    with pytest.raises(FileNotFoundError):
        voice.synthesize("سلام", str(tmp_path / "missing.onnx"), str(tmp_path / "out.wav"))


def test_offline_roundtrip_propagates_timeout(monkeypatch):
    import my_ai.voice as voice
    import subprocess
    def fail(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="voice", timeout=1)
    monkeypatch.setattr(voice, "transcribe", fail)
    import pytest
    with pytest.raises(subprocess.TimeoutExpired):
        voice.offline_roundtrip("audio.wav", "whisper.bin", "piper.onnx", "out.wav")
