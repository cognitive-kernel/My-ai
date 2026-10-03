import importlib.util


_spec = importlib.util.spec_from_file_location("hardcoded_config_inventory", "scripts/hardcoded_config_inventory.py")
assert _spec and _spec.loader
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_inventory_covers_all_hardcoded_configuration_categories(tmp_path):
    source = tmp_path / "sample.py"
    source.write_text(
        """
PROVIDER_MODEL = "ollama"
SERVICE_URL = "http://127.0.0.1"
REQUEST_TIMEOUT = 30
RETRY_LIMIT = 3
FEATURE_ENABLED = True
SECURITY_POLICY = "approval"
PROJECT_PATH = "/tmp/project"
REVIEW_INTERVAL = 3600
""",
        encoding="utf-8",
    )
    items = _module.inventory(tmp_path)
    categories = {item["category"] for item in items}
    assert {
        "provider_model_names",
        "urls",
        "timeouts_retries_limits",
        "feature_flags",
        "policies",
        "filesystem_paths",
        "schedules_intervals",
    } <= categories


def test_inventory_summary_is_machine_readable(tmp_path):
    (tmp_path / "sample.py").write_text("MODEL_NAME = 'test-model'\n", encoding="utf-8")
    summary = _module.summarize(_module.inventory(tmp_path))
    assert summary["total"] == 1
    assert summary["categories"]["provider_model_names"] == 1
    assert summary["items"][0]["file"] == "sample.py"
