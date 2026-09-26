import os
import pytest
from playwright.sync_api import Page

@pytest.mark.e2e
def test_browser_authenticated_surface(page: Page, base_url: str):
    username = "e2e-admin"
    password = os.getenv("E2E_PASSWORD", "test-password")
    register = page.request.post(
        f"{base_url}/auth/register",
        data={"username": username, "password": password, "display_name": "E2E"},
    )
    assert register.status in (200, 409)
    if register.status == 409:
        login = page.request.post(
            f"{base_url}/auth/login",
            data={"username": username, "password": password},
        )
        assert login.ok
    page.goto(f"{base_url}/")
    assert page.locator("body").count() == 1
    for path in ("/learning/status", "/scheduler/status", "/voice/status",
                 "/self-update/status", "/self-repair/status",
                 "/memory/knowledge?limit=5", "/skills"):
        response = page.request.get(f"{base_url}{path}")
        assert response.status == 200, path
        assert response.text
    learning = page.request.get(f"{base_url}/learning/status").json()
    assert "languages" in learning and "courses" in learning
    voice = page.request.get(f"{base_url}/voice/status").json()
    assert "offline" in voice or "offline_ready" in voice
