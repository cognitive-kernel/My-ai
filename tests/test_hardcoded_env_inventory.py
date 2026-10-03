import ast

from scripts.hardcoded_env_inventory import inventory


def test_inventory_finds_literal_os_getenv(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text("import os\nvalue = os.getenv('MYAI_SAMPLE', 'x')\n", encoding="utf-8")
    items = inventory(tmp_path)
    assert items == [{
        "file": "sample.py",
        "line": 2,
        "name": "MYAI_SAMPLE",
        "call": "os.getenv('MYAI_SAMPLE', 'x')",
    }]


def test_inventory_ignores_non_environment_calls(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text("import os\nvalue = os.path.exists('x')\n", encoding="utf-8")
    assert inventory(tmp_path) == []
