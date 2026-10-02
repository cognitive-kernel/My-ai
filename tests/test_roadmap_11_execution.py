from my_ai.settings_store import SETTING_REGISTRY


def test_execution_limits_are_configurable():
    for key in ("execution.mode", "execution.timeout_seconds", "execution.max_output_chars", "execution.max_memory_mb", "execution.max_cpu_seconds"):
        assert key in SETTING_REGISTRY
        spec = SETTING_REGISTRY[key]
        assert "default" in spec and "description" in spec
