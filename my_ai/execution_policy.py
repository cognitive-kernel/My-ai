from __future__ import annotations

from typing import Any


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
    """Allow a project side effect only after a concrete semantic route.

    The router owns semantic interpretation. This gate validates the structured
    decision and prevents malformed, low-confidence, or non-actionable turns
    from crossing the side-effect boundary. It intentionally contains no
    trigger-word or phrase list.
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

    current = _text(message)
    goal = _text(args.get("goal"))
    if len(current) < _MIN_CONCRETE_REQUEST_LENGTH or len(goal) < _MIN_CONCRETE_REQUEST_LENGTH:
        return False

    if action in _SIDE_EFFECT_ACTIONS:
        return True

    if action == _CONTINUATION_ACTION:
        # Continuation is never an independent authorization to build. It may
        # cross the project boundary only when persisted state proves that a
        # project-side-effect task is already pending.
        runtime_state = state if isinstance(state, dict) else {}
        pending = _text(runtime_state.get("pending_project_action"))
        last_intent = _text(runtime_state.get("last_intent"))
        if pending not in _SIDE_EFFECT_ACTIONS or last_intent != "coding":
            return False
        prior_goal = _text(runtime_state.get("current_goal"))
        return len(prior_goal) >= _MIN_CONCRETE_REQUEST_LENGTH

    return False
