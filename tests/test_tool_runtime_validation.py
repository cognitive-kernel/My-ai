from my_ai.tool_runtime import execute_registered_tool


def test_tool_runtime_validates_required_input():
    result = execute_registered_tool(
        name="demo",
        input_payload={},
        input_schema={"type":"object","required":["value"]},
        execute=lambda payload: payload["value"],
        authorize=lambda name: True,
    )
    assert result.status == "failed"
    assert "missing required" in result.error
