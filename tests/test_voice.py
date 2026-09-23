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
