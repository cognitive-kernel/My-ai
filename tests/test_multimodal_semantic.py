from pathlib import Path


def test_media_semantic_analysis_uses_local_llm(monkeypatch, tmp_path: Path):
    import my_ai.multimodal as multimodal
    target = tmp_path / "sample.wav"
    target.write_bytes(b"fake")
    monkeypatch.setattr(multimodal, "inspect_file", lambda p: {"name": "sample.wav", "read_only": True})
    monkeypatch.setattr(multimodal, "detect_type", lambda p: {"kind": "audio"})
    monkeypatch.setattr(multimodal, "_ffprobe", lambda p: {"streams": []})
    monkeypatch.setattr(multimodal, "_transcribe_media", lambda p, kind: {"status": "ok", "text": "جلسه درباره شبکه و خطای DNS بود."})
    monkeypatch.setattr(multimodal, "_ollama_text", lambda prompt: "topics: networking; event: DNS failure")
    result = multimodal.analyze(str(target))
    assert result["semantic_analysis"]
    assert "DNS" in result["semantic_analysis"]
