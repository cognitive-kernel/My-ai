from my_ai.api import app
from my_ai.access_policy import is_auth_exception, is_public_path, permission_for_path

def test_every_mutating_api_route_has_explicit_policy():
    missing = []
    for route in app.routes:
        path = getattr(route, "path", "")
        for method in getattr(route, "methods", set()):
            if method not in {"POST", "PUT", "PATCH", "DELETE"}:
                continue
            if is_public_path(path) or is_auth_exception(path):
                continue
            if permission_for_path(path, method) is None:
                missing.append((method, path))
    assert not missing, missing
