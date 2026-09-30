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
        # The router already sees the conversation state. Requiring a concrete
        # semantic goal here prevents an empty/ambiguous continuation from
        # becoming a project mutation while keeping the gate keyword-free.
        return True

    return False
