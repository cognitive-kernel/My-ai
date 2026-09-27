from __future__ import annotations

from dataclasses import dataclass

PUBLIC_PATHS = frozenset({
    "/", "/login", "/register", "/auth/register", "/auth/login",
    "/auth/logout", "/auth/register/status", "/health", "/health/metrics",
    "/openapi.json", "/docs", "/redoc",
})

TOOL_RULES = (
    ("/git/", "github"),
    ("/security/", "security"),
    ("/code/run", "code-execution"),
    ("/code/generate", "code-generation"),
    ("/chat", "chat"),
    ("/learn/url", "learning"),
    ("/learning/", "learning"),
    ("/scheduler/", "scheduler"),
    ("/backup/", "database"),
    ("/voice/", "voice"),
    ("/skills", "skill-engine"),
    ("/models/", "models"),
    ("/memory/search", "memory"),
    ("/web/", "web"),
    ("/projects/", "projects"),
    ("/eval/", "eval"),
    ("/self-update/", "self-update"),
    ("/self-repair/", "self-repair"),
    ("/self-diagnostics/", "self-diagnostics"),
    ("/help/", "help"),
    ("/auth/me", "auth"),
    ("/memory/", "memory"),
    ("/runtime/", "runtime"),
    ("/languages", "learning"),
    ("/admin/", "admin"),
    ("/settings/", "admin"),
    ("/tools/", "tools"),
    ("/files/", "files"),
    ("/image/", "image-generation"),
)

PATH_ACTIONS = {
    "/git/token": "write",
    "/git/logout": "write",
}

@dataclass(frozen=True)
class Permission:
    tool: str
    action: str

def permission_for_path(path: str, method: str) -> tuple[str, str] | None:
    method = method.upper()
    for prefix, tool in TOOL_RULES:
        if path.startswith(prefix) or path == prefix.rstrip("/"):
            action = PATH_ACTIONS.get(
                path,
                "read" if method == "GET"
                else "write" if method in {"PUT", "PATCH", "DELETE"}
                else "execute",
            )
            return tool, action
    return None

def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith("/docs/")

def is_auth_exception(path: str) -> bool:
    return path in {"/auth/login", "/auth/logout", "/auth/register", "/auth/register/status"}

def is_mutation(method: str) -> bool:
    return method.upper() in {"POST", "PUT", "PATCH", "DELETE"}

def read_only_blocked(read_only: bool, method: str, path: str) -> bool:
    return bool(read_only and is_mutation(method) and not is_auth_exception(path) and not path.startswith("/docs/"))


def assert_mutation_allowed(operation: str) -> None:
    """Process-wide mutation guard used by non-HTTP subsystems too."""
    import os
    if os.getenv("MYAI_READ_ONLY", "false").strip().lower() == "true":
        raise PermissionError(f"MYAI_READ_ONLY blocks mutation: {operation}")
