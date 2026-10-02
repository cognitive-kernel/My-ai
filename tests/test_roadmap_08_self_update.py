from my_ai.settings_store import SETTING_REGISTRY


def test_self_update_and_repair_controls_exist():
    for key in ("self_update.require_approval", "self_update.snapshot_before_apply", "self_update.rollback_on_failure", "self_repair.require_approval"):
        assert key in SETTING_REGISTRY
        assert SETTING_REGISTRY[key]["type"] == "enum"
