from __future__ import annotations

import ast
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "my_ai" / "api.py"


def public_routes() -> list[tuple[str, str]]:
    tree = ast.parse(APP.read_text(encoding="utf-8-sig"))
    routes: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "app":
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        routes.append((str(decorator.args[0].value), decorator.func.attr.upper()))
    return sorted(set(routes))


def env_references() -> set[str]:
    result: set[str] = set()
    for path in (ROOT / "my_ai").rglob("*.py"):
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for line in text.splitlines():
            marker = "os.getenv(\""
            if marker in line:
                result.add(line.split(marker, 1)[1].split("\"", 1)[0])
    return result


def audit() -> dict:
    routes = public_routes()
    policy = (ROOT / "my_ai" / "access_policy.py").read_text(encoding="utf-8-sig")
    missing_policy = [path for path, method in routes if path not in {"/", "/health", "/docs", "/redoc", "/openapi.json"} and path not in policy]
    required_env = {"DB_PATH", "OLLAMA_BASE_URL", "OLLAMA_MODEL", "FALLBACK_MODEL", "MYAI_OFFLINE_STRICT"}
    env = env_references()
    return {
        "route_count": len(routes),
        "routes": routes,
        "missing_policy_exact_or_prefix": missing_policy,
        "required_environment_variables_documented": sorted(required_env & env),
        "required_environment_variables_missing": sorted(required_env - env),
    }


def main() -> int:
    result = audit()
    print(result)
    return 1 if result["missing_policy_exact_or_prefix"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
