from my_ai import watchdog


def test_watchdog_rolls_back_unhealthy_activation(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(watchdog, "ROOT", tmp_path)
    monkeypatch.setattr(watchdog, "LESSONS", tmp_path / "lessons.jsonl")
    monkeypatch.setattr(watchdog, "_pid_alive", lambda pid: False)

    class Child:
        def poll(self): return None
        def terminate(self): calls.append(("terminate",))
        def wait(self, timeout=0): calls.append(("wait", timeout))
        def kill(self): calls.append(("kill",))

    monkeypatch.setattr(watchdog.subprocess, "Popen", lambda *args, **kwargs: calls.append(("popen", args[0])) or Child())
    monkeypatch.setattr(watchdog.httpx, "get", lambda *args, **kwargs: type("R", (), {"status_code": 503})())
    monkeypatch.setattr(watchdog, "_git", lambda *args: calls.append(("git", args)) or type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    monkeypatch.setattr(watchdog.time, "sleep", lambda _: None)
    monkeypatch.setattr(watchdog.time, "time", lambda: 100.0)
    import sys
    monkeypatch.setattr(sys, "argv", ["watchdog", "--pid", "1", "--rollback", "backup", "--timeout", "10", "--url", "http://127.0.0.1:8000/health", "--command", "python -c pass"])
    assert watchdog.main() == 1
    assert any(item[0] == "git" and item[1][:2] == ("reset", "--hard") for item in calls)


def test_watchdog_restores_database_snapshot_after_failed_health(monkeypatch, tmp_path):
    snapshot = tmp_path / "snapshot.sqlite"
    target = tmp_path / "db.sqlite"
    snapshot.write_text("snapshot", encoding="utf-8")
    monkeypatch.setattr(watchdog, "_record_lesson", lambda *args, **kwargs: None)
    monkeypatch.setattr(watchdog, "_pid_alive", lambda pid: False)
    monkeypatch.setattr(watchdog.httpx, "get", lambda *args, **kwargs: type("R", (), {"status_code": 503})())
    monkeypatch.setattr(watchdog, "_git", lambda *args: type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})())
    class Child:
        def poll(self): return None
        def terminate(self): pass
        def wait(self, timeout=0): pass
    monkeypatch.setattr(watchdog.subprocess, "Popen", lambda *args, **kwargs: Child())
    monkeypatch.setattr(watchdog.time, "sleep", lambda _: None)
    monkeypatch.setattr(watchdog.time, "time", lambda: 100.0)
    import sys
    monkeypatch.setattr(sys, "argv", ["watchdog", "--pid", "1", "--rollback", "backup", "--timeout", "10", "--command", "python -c pass", "--db-snapshot", str(snapshot), "--db-path", str(target)])
    assert watchdog.main() == 1
    assert target.read_text(encoding="utf-8") == "snapshot"
