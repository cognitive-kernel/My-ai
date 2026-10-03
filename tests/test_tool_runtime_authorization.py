from my_ai.tool_runtime import execute_registered_tool


def test_tool_runtime_authorizes_before_execute():
    called = []
    result = execute_registered_tool(
        name="demo",
        input_payload={"value":"x"},
        input_schema={"type":"object","required":["value"]},
        execute=lambda payload: called.append(payload),
        authorize=lambda name: False,
    )
    assert result.status == "denied"
    assert called == []
