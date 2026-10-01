from my_ai.advanced_agent import (
    Capability, CapabilityRegistry, CompletionReport, ContextBudgetManager, ContextItem,
    EvalCase, EvaluationHarness, Evidence, EvidenceGraph, EvidenceStore, KnowledgeVersionStore,
    ModelProfile, ModelRouter, OperationRisk, PolicyEngine, ResourceScheduler, ResourceSnapshot,
    RuntimeMode, TaskProfile, TraceNode,
)


def test_model_router_respects_hardware_and_capabilities():
    models = [ModelProfile("small", 8192, ram_gb=2, quality=.5, speed=.95, capabilities=frozenset({"chat"})), ModelProfile("coder", 16384, ram_gb=6, quality=.9, speed=.7, capabilities=frozenset({"chat", "code"}))]
    choice = ModelRouter().choose(models, TaskProfile(complexity=.8, context_tokens=8000, required_capabilities=frozenset({"code"})), ResourceSnapshot(8))
    assert choice.model.name == "coder"


def test_model_router_fails_closed_when_resources_are_insufficient():
    try:
        ModelRouter().choose([ModelProfile("big", 32768, ram_gb=16, capabilities=frozenset({"chat"}))], TaskProfile(context_tokens=10000), ResourceSnapshot(4))
    except RuntimeError as exc:
        assert "no model" in str(exc)
    else:
        raise AssertionError("router must fail closed")


def test_context_budget_keeps_high_priority_items():
    pack = ContextBudgetManager().pack([ContextItem("history", "low", .1, 5), ContextItem("requirement", "high", 1.0, 5), ContextItem("evidence", "medium", .8, 5)], 10)
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


def test_capability_registry_and_online_policy_are_explicit():
    registry = CapabilityRegistry([Capability("web", OperationRisk.NETWORK, offline=False)])
    policy = PolicyEngine({"web": registry.get("web")})
    try:
        policy.authorize("web", mode=RuntimeMode.ONLINE)
    except PermissionError:
        pass
    else:
        raise AssertionError("online access must be explicit")
    policy.authorize("web", approved=True, mode=RuntimeMode.ONLINE)


def test_evidence_store_preserves_multiple_sources():
    store = EvidenceStore()
    store.add(Evidence("Python uses rule A", "source-a", .7))
    store.add(Evidence("Python uses rule B", "source-b", .8))
    assert len(store.for_claim("Python")) == 2
    assert store.conflicts("Python")


def test_knowledge_versioning_keeps_history_and_one_active_version():
    store = KnowledgeVersionStore()
    first = store.add("python", "old", "docs-v1")
    second = store.add("python", "new", "docs-v2")
    assert first.version == 1 and second.version == 2
    assert store.active("python") == second
    assert len(store.history("python")) == 2


def test_evidence_graph_requires_valid_trace_edges():
    graph = EvidenceGraph()
    graph.add_node(TraceNode("req", "requirement", "build"))
    graph.add_node(TraceNode("test", "validation", "pytest"))
    graph.link("req", "validated-by", "test")
    assert ("req", "validated-by", "test") in graph.edges


def test_completion_report_is_evidence_based():
    assert CompletionReport("goal", ("req",), ("pytest:pass",)).complete
    assert not CompletionReport("goal", ("req",), (), ("blocked",)).complete


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
