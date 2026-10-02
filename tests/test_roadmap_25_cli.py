from pathlib import Path


def test_admin_operations_are_backed_by_cli_entrypoints():
    assert Path("scripts/myai_admin.py").exists()
    assert Path("scripts/myai_catalog.py").exists()
    assert Path("scripts/myai_control.py").exists()
