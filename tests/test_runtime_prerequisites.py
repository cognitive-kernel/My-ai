from my_ai.runtime_prerequisites import runtime_status


def test_runtime_status_is_non_mutating(monkeypatch):
    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "my_ai.runtime_prerequisites.urllib.request.urlopen",
        lambda *args, **kwargs: Response(),
    )
    monkeypatch.setattr("my_ai.runtime_prerequisites._missing_python", lambda: [])
    monkeypatch.setattr("my_ai.runtime_prerequisites._command_missing", lambda: [])
    monkeypatch.setattr("my_ai.runtime_prerequisites.shutil.which", lambda name: "/usr/bin/" + name)
    result = runtime_status()
    assert result["ok"] is True
    assert result["checks"]["ollama"] is True
    assert result["checks"]["voice_tools"] is True
