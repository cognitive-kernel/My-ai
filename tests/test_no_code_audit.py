import importlib.util


_spec = importlib.util.spec_from_file_location("no_code_audit", "scripts/no_code_audit.py")
assert _spec and _spec.loader
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
scan = _module.scan


def test_inventory_classifies_configuration_categories(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text(
        """
PROVIDER_NAME = "ollama"
MODEL_NAME = "llama"
BASE_URL = "http://127.0.0.1:8000"
REQUEST_TIMEOUT = 30
FEATURE_ENABLED = True
SECURITY_POLICY = "deny"
DATA_PATH = "data/app.db"
SCHEDULE_INTERVAL = 60
""",
        encoding="utf-8",
    )
    kinds = {item["kind"] for item in scan(tmp_path)}
    assert {"provider_model", "url", "timeout_retry_limit", "feature_flag", "policy", "filesystem_path", "schedule_interval"} <= kinds


def test_inventory_reports_getenv_with_name(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text("import os\nvalue = os.getenv('MYAI_SAMPLE', 'x')\n", encoding="utf-8")
    items = scan(tmp_path)
    assert any(item["kind"] == "env" and item["name"] == "MYAI_SAMPLE" for item in items)
