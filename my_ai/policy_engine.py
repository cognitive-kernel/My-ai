from __future__ import annotations

from dataclasses import dataclass
from fastapi import HTTPException

from .access_policy import permission_for_path, read_only_blocked
from .auth import tool_allowed

@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    tool: str | None = None
    action: str | None = None
    reason: str = ""

class PolicyEngine:
    """Single deny-by-default route policy for all API mutations and executions."""
    def decide(self, *, user, method: str, path: str, read_only: bool) -> PolicyDecision:
        if read_only_blocked(read_only, method, path):
            return PolicyDecision(False, reason="read_only")
        permission = permission_for_path(path, method)
        if permission is None and method.upper() != "GET":
            return PolicyDecision(False, reason="unmapped_write_or_execute_route")
        if permission is None:
            return PolicyDecision(True)
        tool, action = permission
        if user is None:
            return PolicyDecision(False, tool, action, "authentication_required")
        if user["role"] == "admin":
            return PolicyDecision(True, tool, action)
        if not tool_allowed(user, tool, action):
            return PolicyDecision(False, tool, action, "permission_denied")
        return PolicyDecision(True, tool, action)

    def enforce(self, **kwargs) -> PolicyDecision:
        decision = self.decide(**kwargs)
        if not decision.allowed:
            code = 423 if decision.reason == "read_only" else 403
            raise HTTPException(code, f"Policy denied: {decision.reason}")
        return decision

policy = PolicyEngine()

def audit_payload(request_id: str, method: str, path: str, status: int) -> str:
    return f"request_id={request_id} method={method} path={path} status={status}"