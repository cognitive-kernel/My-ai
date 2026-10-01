from my_ai.advanced_agent import (
    Capability,
    ContextBudgetManager,
    ContextItem,
    EvalCase,
    EvaluationHarness,
    Evidence,
    EvidenceStore,
    ModelProfile,
    ModelRouter,
    OperationRisk,
    PolicyEngine,
    ResourceScheduler,
    ResourceSnapshot,
    TaskProfile,
)


def test_model_router_respects_hardware_and_capabilities():
    models = [
        ModelProfile("small", 8192, ram_gb=2, quality=.5, speed=.95, capabilities=frozenset({"chat"})),
        ModelProfile("coder", 16384, ram_gb=6, quality=.9, speed=.7, capabilities=frozenset({"chat", "code"})),
    ]
    choice = ModelRouter().choose(models, TaskProfile(complexity=.8, context_tokens=8000, required_capabilities=frozenset({"code"})), ResourceSnapshot(8))
    assert choice.model.name == "coder"


def test_model_router_fails_closed_when_resources_are_insufficient():
    models = [ModelProfile("big", 32768, ram_gb=16, capabilities=frozenset({"chat"}))]
    try:
        ModelRouter().choose(models, TaskProfile(context_tokens=10000), ResourceSnapshot(4))
    except RuntimeError as exc:
        assert "no model" in str(exc)
    else:
        raise AssertionError("router must fail closed")


def test_context_budget_keeps_high_priority_items():
    pack = ContextBudgetManager().pack([
        ContextItem("history", "low", priority=.1, tokens=5),
        ContextItem("requirement", "high", priority=1.0, tokens=5),
        ContextItem("evidence", "medium", priority=.8, tokens=5),
    ], 10)
    assert [x.kind for x in pack.items] == ["requirement", "evidence"]
    assert pack.omitted == 1


def test_policy_requires_approval_for_sensitive_tools():
    policy = PolicyEngine({"delete": Capability("delete", OperationRisk.DESTRUCTIVE, requires_approval=True)})
    try:
        policy.authorize("delete")
    except PermissionError:
        pass
    else:
        raise AssertionError("sensitive capability must require approval")
    policy.authorize("delete", approved=True)


def test_evidence_store_preserves_multiple_sources():
    store = EvidenceStore()
    store.add(Evidence("Python uses rule A", "source-a", .7))
    store.add(Evidence("Python uses rule B", "source-b", .8))
    assert len(store.for_claim("Python")) == 2


def test_scheduler_bounds_concurrency():
    scheduler = ResourceScheduler(max_concurrent=1)
    assert scheduler.acquire() is True
    assert scheduler.acquire() is False
    scheduler.release()
    assert scheduler.acquire() is True


def test_evaluation_harness_reports_failures_without_aborting():
    cases = [EvalCase("ok", "a", "A"), EvalCase("bad", "b", "B")]
    results = EvaluationHarness().run(cases, lambda x: x.upper() if x == "a" else "wrong")
    assert [r.passed for r in results] == [True, False]
    assert results[1].detail
