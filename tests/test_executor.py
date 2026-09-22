from my_ai.executor import run_python, settings


def test_executor_runs_python():
    original_mode = settings.exec_mode
    object.__setattr__(settings, "exec_mode", "subprocess")
    try:
        result = run_python("print(2 + 3)")
    finally:
        object.__setattr__(settings, "exec_mode", original_mode)

    assert result.return_code == 0
    assert result.output.strip() == "5"


def test_executor_reports_error():
    original_mode = settings.exec_mode
    object.__setattr__(settings, "exec_mode", "subprocess")
    try:
        result = run_python("raise ValueError('x')")
    finally:
        object.__setattr__(settings, "exec_mode", original_mode)

    assert result.return_code != 0
    assert "ValueError" in result.error
