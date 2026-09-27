from pathlib import Path
import tomllib


def test_pyproject_is_dependency_source_of_truth():
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["dependencies"]
    assert Path("requirements.txt").read_text(encoding="utf-8").strip() == ""
    lock = Path("requirements.lock").read_text(encoding="utf-8")
    assert "pyproject.toml remains the dependency source of truth" in lock
