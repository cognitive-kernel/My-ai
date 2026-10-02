from fastapi.testclient import TestClient
from my_ai.settings_feature import router


def test_gui_action_and_catalog_routes_exist():
    paths = {getattr(route, "path", "") for route in router.routes}
    assert "/settings/ui-actions" in paths
    assert "/settings/providers" in paths
    assert "/settings/models" in paths
