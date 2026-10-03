import time

from my_ai.tool_runtime import execute_registered_tool


def test_tool_runtime_enforces_timeout():
    result = execute_registered_tool(
        name="slow",
        input_payload={},
        input_schema={"type":"object"},
        execute=lambda payload: time.sleep(0.2),
        authorize=lambda name: True,
        timeout_seconds=0.05,
    )
    assert result.status == "timeout"
