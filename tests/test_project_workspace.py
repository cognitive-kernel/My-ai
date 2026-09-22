from pathlib import Path

from my_ai import project_workspace


def test_project_workspace_creates_named_directory(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    monkeypatch.setattr(project_workspace, "PROJECTS_ROOT", root)
    root.mkdir()

    workspace = project_workspace.create_project_workspace("مدیریت کاربران")

    assert workspace.parent == root
    assert workspace.name == "مدیریت-کاربران"
    assert workspace.is_dir()

    files = project_workspace.write_project_files(
        workspace,
        "Python",
        "مدیریت کاربران",
        "print('ok')",
    )
    assert (workspace / "main.py").read_text(encoding="utf-8") == "print('ok')"
    assert (workspace / "README.md").exists()
    assert "projects/مدیریت-کاربران/main.py" in files


def test_project_workspace_avoids_overwrite(tmp_path, monkeypatch):
    root = tmp_path / "projects"
    monkeypatch.setattr(project_workspace, "PROJECTS_ROOT", root)
    root.mkdir()
    (root / "demo").mkdir()

    workspace = project_workspace.create_project_workspace("demo")

    assert workspace.name == "demo-2"
