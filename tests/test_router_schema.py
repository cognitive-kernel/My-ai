from my_ai.router import Intent, ROUTER_TOOL_SCHEMA, _parse_router_payload, router_tool_call


def test_router_schema_is_strictly_structured():
    assert ROUTER_TOOL_SCHEMA["name"] == "route_request"
    assert ROUTER_TOOL_SCHEMA["parameters"]["additionalProperties"] is False
    assert "confidence" in ROUTER_TOOL_SCHEMA["parameters"]["required"]


def test_router_tool_call_never_implies_authorization():
    intent = Intent("code_execution", 0.91, True, {"language": "python"}, ("code_execution",))
    call = router_tool_call(intent)
    assert call["name"] == "route_request"
    assert call["arguments"]["primary"] == "code_execution"
    assert "authorized" not in call["arguments"]


def test_router_payload_requires_schema_fields():
    payload = '{"primary":"chat","intents":["chat"],"confidence":0.8,"language":null,"topic":null,"goal":null}'
    assert _parse_router_payload(payload)["primary"] == "chat"
