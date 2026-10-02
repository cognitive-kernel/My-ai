from pathlib import Path

from my_ai.test_runner import run_test_suite


def test_filewise_runner_stops_on_first_timeout(tmp_path, monkeypatch):
    (tmp_path / "my_ai").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_one.py").write_text("def test_ok(): pass\n", encoding="utf-8")
    calls = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        if args[1:4] == ["-m", "compileall", "-q"]:
            return Result()
        raise __import__("subprocess").TimeoutExpired(args, 30)

    monkeypatch.setattr("my_ai.test_runner.subprocess.run", fake_run)
    ok, details = run_test_suite(Path(tmp_path), per_file_timeout=30)
    assert ok is False
    assert "should not be used" in details
    assert len(calls) == 2
