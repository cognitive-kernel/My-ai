from my_ai.advanced_agent import AgentOS, EventWorkflow


def test_agent_os_has_shared_lifecycle_registries():
    os = AgentOS()
    session = os.create_session({"source": "test"})
    task = os.create_task(session["id"], "demo", {})
    assert task["session_id"] == session["id"]
    assert task["status"] == "queued"
    assert os.events is not None
    assert os.evaluations is not None


def test_event_bus_supports_idempotent_events():
    bus = EventWorkflow()
    seen = []
    bus.on("evt", lambda payload: seen.append(payload))
    bus.emit("evt", 1, event_id="e1")
    bus.emit("evt", 1, event_id="e1")
    assert seen == [1]
