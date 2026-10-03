from pathlib import Path

import pytest

from my_ai.control_plane import namespace_catalog
from my_ai.module_gui import module_form_catalog, module_form_schema
from my_ai import settings_feature as sf


@pytest.mark.timeout(30)
def test_every_control_plane_namespace_has_a_graphical_form_schema():
    schemas = {item["namespace"]: item for item in module_form_catalog()}
    namespaces = namespace_catalog()
    assert set(schemas) == set(namespaces)
    for namespace in namespaces:
        assert schemas[namespace]["fields"]
        assert schemas[namespace]["timeout_seconds"] == 30


@pytest.mark.timeout(30)
def test_module_form_schema_is_typed_and_not_json_only():
    for namespace in namespace_catalog():
        fields = module_form_schema(namespace)["fields"]
        assert any(field["type"] in {"text", "number", "select", "boolean"} for field in fields)


@pytest.mark.timeout(30)
def test_settings_exposes_module_form_route_and_gui_script():
    paths = {getattr(route, "path", "") for route in sf.router.routes}
    assert "/settings/module-forms" in paths
    script = Path("my_ai/settings_script.js").read_text(encoding="utf-8")
    assert "/settings/module-forms" in script
    assert "AbortController" in script
    assert "30000" in script
    assert "moduleGuiInput" in script


@pytest.mark.timeout(30)
def test_module_gui_uses_shared_control_plane_persistence():
    source = Path("my_ai/settings_script.js").read_text(encoding="utf-8")
    assert "/settings/control-plane/" in source
    assert 'method:"PUT"' in source
    assert "payload:payload" in source
