from my_ai.domain.router import ROUTER_SCHEMA, _parse_router_payload
from my_ai.application.router import build_router_service


def valid_payload(**overrides):
    value = {
        "primary": "learning",
        "intents": ["learning", "coding"],
        "action": "continue_task",
        "confidence": 0.91,
        "language": "fa",
        "topic": "Python",
        "goal": "learn then implement",
        "project_path": None,
        "target": "software artifact",
        "urls": [],
    }
    value.update(overrides)
    return value


class Client:
    def __init__(self, payload):
        self.payload = payload

    def structured_chat_json(self, prompt, schema, system=None):
        assert schema == ROUTER_SCHEMA
        assert system and "semantic router" in system
        return self.payload


def test_router_schema_rejects_missing_fields():
    try:
        _parse_router_payload('{"primary":"chat"}')
    except ValueError:
        return
    raise AssertionError("missing structured fields must be rejected")


def test_router_schema_rejects_extra_fields():
    value = valid_payload(extra="must fail")
    try:
        _parse_router_payload(__import__("json").dumps(value))
    except ValueError:
        return
    raise AssertionError("extra structured fields must be rejected")


def test_structured_router_handles_ambiguous_multi_intent():
    result = build_router_service(Client(valid_payload())).classify("پایتون را یاد بگیر و بعد یک مثال بنویس")
    assert result.intents == ("learning", "coding")
    assert result.confidence == 0.91


def test_domain_router_has_no_keyword_tables_or_regex_fallback():
    source = __import__("pathlib").Path("my_ai/domain/router.py").read_text(encoding="utf-8")
    assert "_INTENT_PATTERNS" not in source
    assert "import re" not in source
    assert "_normalize(" not in source


def test_artifact_false_positive_is_demoted_to_chat():
    payload = valid_payload(
        primary="coding",
        intents=["coding"],
        action="create_artifact",
        confidence=0.99,
        language=None,
        topic=None,
        goal="create artifact",
        project_path=None,
    )
    result = build_router_service(Client(payload)).classify("سلام")
    assert result.name == "chat"
    assert result.args["action"] == "answer"



def test_artifact_normalization_cannot_reenable_side_effect():
    payload = valid_payload(
        primary="learning",
        intents=["learning"],
        action="create_artifact",
        confidence=0.99,
        language=None,
        topic=None,
        goal="create artifact",
        project_path=None,
    )
    result = build_router_service(Client(payload)).classify("سلام")
    assert result.name == "chat"
    assert result.args["action"] == "answer"

def test_concrete_artifact_goal_remains_coding():
    payload = valid_payload(
        primary="coding",
        intents=["coding"],
        action="create_artifact",
        confidence=0.99,
        language="Python",
        topic="calculator",
        goal="create a desktop calculator application with tests",
        project_path=None,
    )
    result = build_router_service(Client(payload)).classify("یک برنامه ماشین حساب دسکتاپ با تست بساز")
    assert result.name == "coding"
    assert result.args["action"] == "create_artifact"


def test_semantic_target_can_authorize_without_language_or_topic():
    payload = valid_payload(
        primary="coding",
        intents=["coding"],
        action="create_artifact",
        confidence=0.99,
        language=None,
        topic=None,
        goal="create a desktop application for tracking expenses",
        project_path=None,
        target="desktop expense tracking application",
    )
    result = build_router_service(Client(payload)).classify("I need an application for tracking expenses")
    assert result.name == "coding"
    assert result.args["action"] == "create_artifact"
    assert result.args["target"] == "desktop expense tracking application"


def test_router_tool_contract_preserves_semantic_target():
    from my_ai.domain.router import Intent, router_tool_call
    intent = Intent("coding", 0.95, args={"action": "create_artifact", "goal": "create app", "target": "desktop app"})
    arguments = router_tool_call(intent)["arguments"]
    assert arguments["target"] == "desktop app"
