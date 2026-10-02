from my_ai.settings_feature import router


def test_provider_model_gui_lifecycle_routes_exist():
    paths = {getattr(route, "path", "") for route in router.routes}
    assert "/settings/providers/{provider_id}/health" in paths
    assert "/settings/models/{provider_id}/{model_id:path}" in paths
    assert "/settings/models/{provider_id}/{model_id:path}/health" in paths



def test_provider_and_model_forms_expose_catalog_metadata_controls():
    from my_ai.settings_feature import SETTINGS_HTML
    for field in ("pc_timeout", "pc_capabilities", "pc_version", "pc_enabled"):
        assert f'id=\'{field}\'' in SETTINGS_HTML
    for field in ("mc_context", "mc_limits", "mc_priority", "mc_version", "mc_enabled"):
        assert f'id=\'{field}\'' in SETTINGS_HTML
    assert "JSON.parse(byId(\"pc_capabilities\").value)" in __import__("pathlib").Path("my_ai/settings_script.js").read_text(encoding="utf-8")
    assert "JSON.parse(byId(\"mc_limits\").value)" in __import__("pathlib").Path("my_ai/settings_script.js").read_text(encoding="utf-8")
