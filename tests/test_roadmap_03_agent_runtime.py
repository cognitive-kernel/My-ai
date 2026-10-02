from my_ai.advanced_agent import ContextPlanner, ConfidenceEngine, EventWorkflow, TaskGraph


def test_context_planner_respects_budget():
    plan = ContextPlanner(estimator=lambda text: len(text)).plan(
        [{"content": "1234", "priority": 2}, {"content": "123456", "priority": 1}], 5
    )
    assert plan.estimated_tokens <= 5
    assert plan.items == [{"content": "1234", "priority": 2}]


def test_confidence_engine_selects_verify_band():
    result = ConfidenceEngine().score(source_quality=.6, agreement=.6, freshness=.6, verification=.6, historical_success=.6)
    assert result.action == "verify"
    assert result.score == .6


def test_event_workflow_is_idempotent():
    events = EventWorkflow()
    calls = []
    events.on("x", lambda payload: calls.append(payload))
    assert len(events.emit("x", {"v": 1}, event_id="same")) == 1
    assert events.emit("x", {"v": 1}, event_id="same") == []
    assert len(calls) == 1


def test_task_graph_detects_ready_dependencies():
    graph = TaskGraph()
    graph.add("a", lambda: 1)
    graph.add("b", lambda: 2, deps=("a",))
    assert graph.ready(set()) == ["a"]
    assert graph.ready({"a"}) == ["b"]


def test_agent_system_behavior_and_persona_are_configuration_driven(monkeypatch):
    values = {"agent.system_behavior": "Be concise.", "agent.persona": "Technical maintainer."}
    import importlib
    agent_module = importlib.import_module("my_ai.agent")
    monkeypatch.setattr(agent_module, "get_setting", lambda key, default="": values.get(key, default))
    Agent = agent_module.Agent
    system = Agent(llm=object())._configured_system()
    assert "CONFIGURED SYSTEM BEHAVIOR:\nBe concise." in system
    assert "CONFIGURED PERSONA:\nTechnical maintainer." in system