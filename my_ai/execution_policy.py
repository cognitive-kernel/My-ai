from __future__ import annotations

from typing import Any


# The policy is deliberately small. Semantic interpretation belongs to the
# router; this module only decides whether that interpretation is sufficiently
# concrete to cross the side-effect boundary.
_SIDE_EFFECT_ACTIONS = frozenset({"create_artifact", "modify_artifact"})
_CONTINUATION_ACTION = "continue_task"
_MIN_CONFIDENCE = 0.70
_MIN_CONCRETE_REQUEST_LENGTH = 8


def _args(intent: Any) -> dict[str, Any]:
    value = getattr(intent, "args", None)
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def authorize_project_execution(message: str, intent: Any, state: dict[str, Any] | None = None) -> bool:
    """Return True only when the semantic route is concrete enough for a project side effect.

    No trigger-word or phrase list is used here. The router owns semantic
    interpretation; this gate only validates the structured decision and the
    current conversation state before an executor can mutate the workspace.
    """
    if getattr(intent, "name", "") != "coding":
        return False

    args = _args(intent)
    action = _text(args.get("action"))
    confidence = getattr(intent, "confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        return False
    if confidence < _MIN_CONFIDENCE:
        return False

    goal = _text(args.get("goal"))
    current = _text(message)
    if action in _SIDE_EFFECT_ACTIONS:
        # A real artifact operation needs a concrete semantic goal from the
        # router and a non-trivial current request. This blocks accidental
        # execution from greetings, empty/ambiguous turns, or malformed routes.
        return len(current) >= _MIN_CONCRETE_REQUEST_LENGTH and len(goal) >= _MIN_CONCRETE_REQUEST_LENGTH

    if action == _CONTINUATION_ACTION:
        state = state or {}
        previous_action = _text(state.get("last_action"))
        previous_goal = _text(state.get("current_goal"))
        return bool(previous_goal) and previous_action in {
            "create_artifact",
            "modify_artifact",
            "continue_task",
        }

    return False
