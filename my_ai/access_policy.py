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
    ("/roadmap/", "roadmap"),
)

PATH_ACTIONS = {
    ("POST", "/git/token"): "write",
    ("POST", "/git/logout"): "write",
    ("POST", "/memory/knowledge"): "write",
    ("PUT", "/memory/knowledge/{knowledge_id}"): "write",
    ("GET", "/memory/knowledge/{knowledge_id}/audit"): "read",
    ("POST", "/memory/knowledge/{knowledge_id}/verify"): "write",
    ("POST", "/files/upload"): "write",
    ("POST", "/files/generate/docx"): "write",
    ("POST", "/files/generate/xlsx"): "write",
    ("POST", "/files/generate/pdf"): "write",
    ("POST", "/files/generate/pptx"): "write",
    ("POST", "/files/generate/from-chat"): "write",
    ("POST", "/voice/upload"): "write",
    ("POST", "/backup/database"): "write",
    ("POST", "/backup/export"): "write",
    ("POST", "/backup/import"): "write",
    ("POST", "/backup/restore-database"): "write",
    ("POST", "/self-update/apply"): "write",
    ("POST", "/self-repair/apply"): "write",
    ("POST", "/help/approve/{update_id}"): "write",
    ("POST", "/help/reject/{update_id}"): "write",
    ("POST", "/admin/users"): "write",
    ("PATCH", "/admin/users/{user_id}/active"): "write",
    ("PUT", "/admin/tools"): "write",
    ("POST", "/tools/project"): "execute",
    ("POST", "/tools/python"): "execute",
    ("POST", "/tools/sqlserver/query"): "execute",
    ("POST", "/tools/mysql/query"): "execute",
    ("POST", "/tools/sqlite/query"): "execute",
    ("POST", "/skills/evidence"): "execute",
    ("POST", "/skills/revalidate"): "execute",
    ("POST", "/skills/{skill_id}/sandbox-test"): "execute",
    ("POST", "/skills/reviews"): "write",
    ("POST", "/image/generate"): "execute",
    ("POST", "/chat"): "execute",
    ("POST", "/chat/stream"): "execute",
    ("POST", "/learning/start"): "execute",
    ("POST", "/learning/step"): "execute",
    ("POST", "/learning/{language}/stop"): "execute",
    ("POST", "/learning/{language}/resume"): "execute",
}

@dataclass(frozen=True)
class Permission:
    tool: str
    action: str

def _path_matches(pattern: str, path: str) -> bool:
    if pattern == path:
        return True
    pattern_parts = pattern.strip("/").split("/")
    path_parts = path.strip("/").split("/")
    if len(pattern_parts) != len(path_parts):
        return False
    return all(
        p == actual or (p.startswith("{") and p.endswith("}"))
        for p, actual in zip(pattern_parts, path_parts)
    )


def permission_for_path(path: str, method: str) -> tuple[str, str] | None:
    method = method.upper()
    for prefix, tool in TOOL_RULES:
        if path.startswith(prefix) or path == prefix.rstrip("/"):
            action = next(
                (
                    configured_action
                    for (configured_method, pattern), configured_action in PATH_ACTIONS.items()
                    if configured_method == method and _path_matches(pattern, path)
                ),
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
