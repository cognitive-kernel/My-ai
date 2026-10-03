from my_ai.tool_runtime import execute_registered_tool


def test_tool_runtime_has_trace_and_observe_audit():
    observed = []
    audited = []
    result = execute_registered_tool(
        name="demo",
        input_payload={"value":"ok"},
        input_schema={"type":"object","required":["value"]},
        execute=lambda payload: {"ok": payload["value"]},
        authorize=lambda name: True,
        observe=observed.append,
        audit=audited.append,
        trace_id="trace-test-1",
    )
    assert result.status == "completed"
    assert result.trace_id == "trace-test-1"
    assert observed[0].trace_id == "trace-test-1"
    assert audited[0].status == "completed"
