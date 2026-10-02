from my_ai.settings_store import SETTING_REGISTRY


def test_multimodal_provider_settings_exist():
    assert "multimodal.image_provider" in SETTING_REGISTRY
    assert "multimodal.voice_provider" in SETTING_REGISTRY
    assert SETTING_REGISTRY["multimodal.image_provider"]["type"] == "text"
