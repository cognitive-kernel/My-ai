import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Page

@pytest.mark.e2e
def test_authenticated_file_workflow(page: Page, base_url: str):
    response = page.request.post(
        f"{base_url}/files/upload",
        multipart={"file": {"name": "e2e.txt", "mimeType": "text/plain", "buffer": b"My-AI E2E"}}
    )
    assert response.ok
    payload = response.json()
    assert payload.get("path")
    read = page.request.post(f"{base_url}/files/read", data={"path": payload["path"]})
    assert read.ok
    assert "My-AI E2E" in read.text()
