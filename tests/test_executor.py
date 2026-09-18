from my_ai.executor import run_python


def test_executor_runs_python():
    result = run_python("print(2 + 3)")
    assert result.return_code == 0
    assert result.output.strip() == "5"


def test_executor_reports_error():
    result = run_python("raise ValueError('x')")
    assert result.return_code != 0
    assert "ValueError" in result.error
