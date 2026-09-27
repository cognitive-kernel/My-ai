from my_ai.api import app


def test_knowledge_routes_are_registered_without_duplicates():
    routes = [route for route in app.routes if getattr(route, "path", None) == "/memory/knowledge"]
    methods = {method for route in routes for method in getattr(route, "methods", set())}
    assert len(routes) == 2
    assert methods == {"GET", "POST"}
