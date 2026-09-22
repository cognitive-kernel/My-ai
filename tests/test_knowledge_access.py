from my_ai.api import app


def test_knowledge_route_is_registered_once():
    routes = [route for route in app.routes if getattr(route, "path", None) == "/memory/knowledge"]
    assert len(routes) == 1
