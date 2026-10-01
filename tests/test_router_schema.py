from my_ai.router import Intent, ROUTER_TOOL_SCHEMA, _parse_router_payload, router_tool_call
import json


def test_router_schema_is_strictly_structured():
    assert ROUTER_TOOL_SCHEMA["name"] == "route_request"
    assert ROUTER_TOOL_SCHEMA["parameters"]["additionalProperties"] is False
    assert "confidence" in ROUTER_TOOL_SCHEMA["parameters"]["required"]
    assert "project_path" in ROUTER_TOOL_SCHEMA["parameters"]["required"]
    assert "urls" in ROUTER_TOOL_SCHEMA["parameters"]["required"]


def test_router_tool_call_never_implies_authorization():
    intent = Intent("code_execution", 0.91, True, {"language": "python", "action": "execute"}, ("code_execution",))
    call = router_tool_call(intent)
    assert call["name"] == "route_request"
    assert call["arguments"]["primary"] == "code_execution"
    assert "authorized" not in call["arguments"]


def test_router_payload_requires_schema_fields():
    payload = {
        "primary": "chat", "intents": ["chat"], "action": "answer", "confidence": 0.8,
        "language": None, "topic": None, "goal": None, "project_path": None, "target": None, "urls": [],
    }
    assert _parse_router_payload(json.dumps(payload))["primary"] == "chat"


def test_router_payload_rejects_invalid_confidence():
    payload = {
        "primary": "chat", "intents": ["chat"], "confidence": 2,
        "language": None, "topic": None, "goal": None, "project_path": None, "urls": [],
    }
    try:
        _parse_router_payload(json.dumps(payload))
    except ValueError:
        return
    raise AssertionError("invalid confidence must be rejected")
