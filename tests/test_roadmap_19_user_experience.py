from pathlib import Path


def test_settings_surface_and_gui_action_registry_exist():
    assert Path("my_ai/settings_feature.py").exists()
    assert Path("my_ai/settings_script.js").exists()
    assert Path("my_ai/ui_actions.py").exists()
