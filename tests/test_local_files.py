from pathlib import Path

from my_ai.local_files import inspect_file, read_text, workspace_path


def test_inspect_and_read_local_file_without_mutation(tmp_path: Path):
    target = tmp_path / "sample.txt"
    target.write_text("hello", encoding="utf-8")

    info = inspect_file(str(target))
    assert info["name"] == "sample.txt"
    assert info["read_only"] is True
    assert info["sha256"]
    assert read_text(str(target)) == "hello"
    assert target.read_text(encoding="utf-8") == "hello"


def test_workspace_path_cannot_escape_workspace():
    path = workspace_path("../../outside.txt")
    assert path.parent.name == "files"
    assert path.name == "outside.txt"
