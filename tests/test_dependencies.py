from pathlib import Path
import tomllib


def test_pyproject_is_dependency_source_of_truth():
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["dependencies"]
    assert Path("requirements.txt").read_text(encoding="utf-8").strip() == "-e ."
    lock = Path("requirements.lock").read_text(encoding="utf-8")
    assert "pyproject.toml remains the dependency source of truth" in lock


def test_runtime_dependencies_are_pinned_in_lock():
    import re
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    lock_lines = Path("requirements.lock").read_text(encoding="utf-8").splitlines()
    pinned = {line.split("==", 1)[0].lower() for line in lock_lines if "==" in line and not line.lstrip().startswith("#")}
    for spec in data["project"]["dependencies"]:
        name = re.split(r"[<>=!~;\[]", spec, maxsplit=1)[0].strip().lower()
        assert name in pinned, f"{name} is missing from requirements.lock"
