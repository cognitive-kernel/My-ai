from __future__ import annotations

import os
from pathlib import Path

from my_ai.access_policy import is_public_path, permission_for_path
from my_ai.api import app


def audit_routes() -> dict:
    missing_policy = []
    protected_without_auth = []
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set()) or set()
        if not path or not methods:
            continue
        for method in methods:
            if method == "HEAD" and "GET" in methods:
                continue
            if is_public_path(path) or permission_for_path(path, method):
                continue
            missing_policy.append(f"{method} {path}")
        if not is_public_path(path) and not permission_for_path(path, next(iter(methods))):
            protected_without_auth.append(path)
    required_env_defaults = {
        "MYAI_READ_ONLY": os.getenv("MYAI_READ_ONLY", "false"),
        "MYAI_OFFLINE_STRICT": os.getenv("MYAI_OFFLINE_STRICT", "false"),
        "DB_PATH": os.getenv("DB_PATH", "data/myai.db"),
    }
    return {
        "route_count": len(app.routes),
        "missing_policy": sorted(set(missing_policy)),
        "protected_without_policy": sorted(set(protected_without_auth)),
        "environment_defaults": required_env_defaults,
        "architecture_docs": [
            str(path.relative_to(Path(__file__).resolve().parents[1]))
            for path in (Path(__file__).resolve().parents[1] / "docs").glob("*.md")
        ],
    }


def main() -> int:
    result = audit_routes()
    if result["missing_policy"] or result["protected_without_policy"]:
        print(result)
        return 1
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
