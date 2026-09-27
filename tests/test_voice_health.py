from my_ai import voice

def test_voice_status_is_structured(monkeypatch):
    monkeypatch.setattr(voice, "_whisper_binary", lambda: None)
    monkeypatch.setattr(voice, "_piper_binary", lambda: None)
    result = voice.status()
    assert result["offline_ready"] is False
    assert "probes" in result
