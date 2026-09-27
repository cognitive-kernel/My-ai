from my_ai.api import app


def test_system_prerequisite_route_is_registered():
    assert any(getattr(r, "path", "") == "/files/prerequisites" for r in app.routes)
