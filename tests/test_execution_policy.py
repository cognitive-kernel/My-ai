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
        args={"action": "create_artifact", "goal": "build a Python expense manager"},
        intents=("coding",),
    )
    assert authorize_project_execution("یک برنامه مدیریت هزینه با پایتون ایجاد کن", intent) is True


def test_non_coding_create_route_is_blocked():
    intent = Intent(
        name="chat",
        confidence=0.99,
        args={"action": "create_artifact", "goal": "build a Python expense manager"},
        intents=("chat",),
    )
    assert authorize_project_execution("یک برنامه مدیریت هزینه ایجاد کن", intent) is False


def test_continuation_requires_concrete_goal():
    intent = Intent(
        name="coding",
        confidence=0.95,
        args={"action": "continue_task", "goal": "continue the existing Python project"},
        intents=("coding",),
    )
    assert authorize_project_execution("ادامه بده", intent) is True
