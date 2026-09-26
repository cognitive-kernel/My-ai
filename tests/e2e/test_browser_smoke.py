import os
import pytest

pytest.importorskip("playwright.sync_api")
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

    readiness = page.request.get(f"{base_url}/admin/readiness")
    assert readiness.ok
    readiness_body = readiness.json()
    assert set(("checks", "runtime", "knowledge", "skills", "self_update_policy")) <= set(readiness_body["checks"].keys())

    retrieval = page.request.get(f"{base_url}/eval/retrieval")
    assert retrieval.ok
    retrieval_body = retrieval.json()
    assert "mrr" in retrieval_body and "calibration" in retrieval_body

    skills = page.request.get(f"{base_url}/skills/reviews")
    assert skills.ok
    assert "items" in skills.json()

    page.goto(f"{base_url}/")
    assert page.locator("#dashboard").count() == 1
    assert page.locator("body").count() == 1
