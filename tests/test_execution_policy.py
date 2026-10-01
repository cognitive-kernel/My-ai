from my_ai.domain.router import Intent
from my_ai.execution_policy import authorize_project_execution


def test_greeting_cannot_cross_project_execution_gate():
    intent = Intent(
        name="coding",
        confidence=0.99,
        args={"action": "create_artifact", "goal": "say hello"},
        intents=("coding",),
    )
    assert authorize_project_execution("سلام", intent) is False


def test_low_confidence_project_route_is_blocked():
    intent = Intent(
        name="coding",
        confidence=0.69,
        args={"action": "create_artifact", "goal": "build a Python API"},
        intents=("coding",),
    )
    assert authorize_project_execution("یک API پایتون برای مدیریت هزینه بساز", intent) is False


def test_concrete_semantic_create_route_is_allowed():
    intent = Intent(
        name="coding",
        confidence=0.95,
        args={"action": "create_artifact", "goal": "a personal finance desktop application", "language": "Python", "topic": "expense management"},
        intents=("coding",),
    )
    assert authorize_project_execution("I need a small desktop tool for tracking household spending", intent) is True


def test_non_coding_create_route_is_blocked():
    intent = Intent(
        name="chat",
        confidence=0.99,
        args={"action": "create_artifact", "goal": "build a Python expense manager"},
        intents=("chat",),
    )
    assert authorize_project_execution("یک برنامه مدیریت هزینه ایجاد کن", intent) is False


def test_continuation_without_pending_project_state_is_blocked():
    intent = Intent(
        name="coding",
        confidence=0.95,
        args={"action": "continue_task", "goal": "continue the existing Python project"},
        intents=("coding",),
    )
    assert authorize_project_execution("ادامه بده", intent, {}) is False


def test_continuation_requires_pending_project_state():
    intent = Intent(
        name="coding",
        confidence=0.95,
        args={"action": "continue_task", "goal": "continue the existing Python project"},
        intents=("coding",),
    )
    state = {
        "current_goal": "build the existing Python project",
        "last_intent": "coding",
        "pending_project_action": "create_artifact",
    }
    assert authorize_project_execution("ادامه بده", intent, state) is True


def test_non_project_continuation_state_is_blocked():
    intent = Intent(
        name="coding",
        confidence=0.95,
        args={"action": "continue_task", "goal": "continue the existing Python project"},
        intents=("coding",),
    )
    state = {
        "current_goal": "explain Python decorators",
        "last_intent": "chat",
        "pending_project_action": "",
    }
    assert authorize_project_execution("ادامه بده", intent, state) is False


def test_blocked_create_cannot_poison_continuation_state():
    create_intent = Intent(
        name="coding",
        confidence=0.69,
        args={"action": "create_artifact", "goal": "build a Python expense manager"},
        intents=("coding",),
    )
    state = {}
    assert authorize_project_execution("یک برنامه مدیریت هزینه بساز", create_intent, state) is False
    assert state.get("pending_project_action") is None

    continue_intent = Intent(
        name="coding",
        confidence=0.95,
        args={"action": "continue_task", "goal": "continue the Python project"},
        intents=("coding",),
    )
    assert authorize_project_execution("ادامه بده", continue_intent, state) is False
\n
def test_project_policy_contains_no_phrase_or_keyword_rules():
    from pathlib import Path

    source = Path("my_ai/execution_policy.py").read_text(encoding="utf-8")
    assert "marker" not in source.casefold()
    assert "startswith(" not in source
    assert "endswith(" not in source
    assert "_MIN_CONCRETE_REQUEST_LENGTH" not in source
