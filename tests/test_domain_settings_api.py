import pytest

pytestmark = pytest.mark.timeout(30)


def test_domain_settings_api_routes_and_30_second_client_timeout_exist():
    from my_ai import settings_feature

    assert '"/settings/domain-capabilities"' in settings_feature.__dict__["router"].routes[0].path or any(
        getattr(route, "path", "") == "/settings/domain-capabilities"
        for route in settings_feature.router.routes
    )
    assert any(
        getattr(route, "path", "") == "/settings/domain-capabilities/test"
        for route in settings_feature.router.routes
    )
    assert "setTimeout(function(){c.abort()},30000)" in settings_feature.SETTINGS_HTML
    assert "fetch('/settings/domain-capabilities'" in settings_feature.SETTINGS_HTML
    assert "fetch('/settings/domain-capabilities/test'" in settings_feature.SETTINGS_HTML
