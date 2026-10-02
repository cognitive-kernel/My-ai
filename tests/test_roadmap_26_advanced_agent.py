from my_ai.advanced_agent import (
    AgentOS, ContextPlanner, ConfidenceEngine, EvaluationLab, HybridRetriever,
    KnowledgeGraph, MetaAgent, ReasoningCycle, ResearchPipeline, SkillRegistry,
    TaskGraph, ExecutionBudget, EventWorkflow,
)


def test_advanced_agent_primitives_are_available():
    for cls in (AgentOS, ContextPlanner, ConfidenceEngine, EvaluationLab, HybridRetriever,
                KnowledgeGraph, MetaAgent, ReasoningCycle, ResearchPipeline, SkillRegistry,
                TaskGraph, ExecutionBudget, EventWorkflow):
        assert cls is not None


def test_reasoning_cycle_can_verify_and_early_exit():
    cycle = ReasoningCycle(verifier=lambda value: value == "ok", max_steps=3, early_exit=True)
    result = cycle.run("task", understand=lambda _: "understood", plan=lambda _: "plan",
                       execute=lambda _: "ok")
    assert result["verified"] is True
    assert [step["phase"] for step in result["steps"]].count("execute") == 1


def test_budget_enforces_all_dimensions():
    budget = ExecutionBudget(steps=2, tokens=10, seconds=5, tool_calls=1, cost=1)
    assert budget.allow(steps=2, tokens=10, seconds=5, tool_calls=1, cost=1)
    budget.consume(steps=1, tokens=5, seconds=2, tool_calls=1, cost=.5)
    assert not budget.allow(tool_calls=1, tokens=6)
