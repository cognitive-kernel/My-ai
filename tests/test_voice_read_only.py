from pathlib import Path

from my_ai import voice


def test_transcribe_writes_output_to_temporary_directory(tmp_path: Path, monkeypatch):
    source = tmp_path / "sample.wav"
    model = tmp_path / "model.bin"
    source.write_bytes(b"audio")
    model.write_bytes(b"model")
    calls = {}

    monkeypatch.setattr(voice, "_whisper_binary", lambda: "whisper-cli")

    def fake_run(args, **kwargs):
        calls["args"] = args
        output_base = Path(args[args.index("-of") + 1])
        output_base.with_suffix(".txt").write_text("hello", encoding="utf-8")
        return type("Result", (), {"returncode": 0, "stderr": "", "stdout": ""})()

    monkeypatch.setattr(voice.subprocess, "run", fake_run)
    assert voice.transcribe(str(source), str(model)) == "hello"
    assert not source.with_suffix(".txt").exists()
    assert "-of" in calls["args"]
