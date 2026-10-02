from my_ai.settings_feature import router


def test_provider_model_gui_lifecycle_routes_exist():
    paths = {getattr(route, "path", "") for route in router.routes}
    assert "/settings/providers/{provider_id}/health" in paths
    assert "/settings/models/{provider_id}/{model_id:path}" in paths
    assert "/settings/models/{provider_id}/{model_id:path}/health" in paths
