from my_ai.advanced_agent import Capability, OperationRisk, RuntimeMode, TaskProfile
from my_ai.roadmap_runtime import (
    benchmark_model_selection, model_management,
    add_memory_lesson,
    add_research_trace,
    benchmark_case,
    benchmark_summary,
    choose_model,
    completion_report,
    evidence_edge,
    evidence_node,
    register_capability,
    resolve_conflict,
    trace,
    upsert_knowledge_version,
)


def test_model_selection_is_resource_and_capability_aware(monkeypatch):
    monkeypatch.setenv("ROUTER_MODEL", "router-small")
    monkeypatch.setenv("CODING_MODEL", "coder")
    result = choose_model(TaskProfile(context_tokens=4096, required_capabilities=frozenset({"chat"})))
    assert result["model"]["name"] in {"router-small", "coder", "fallback"}
    assert "resources" in result


def test_capability_policy_is_persisted_and_enforced():
    register_capability(Capability("test-delete", OperationRisk.DESTRUCTIVE, requires_approval=True))
    try:
        from my_ai.roadmap_runtime import authorize_capability
        authorize_capability("test-delete", approved=False, mode=RuntimeMode.LOCAL)
    except PermissionError:
        pass
    else:
        raise AssertionError("approval gate must deny by default")
    authorize_capability("test-delete", approved=True)


def test_knowledge_versions_conflicts_and_evidence_trace():
    from my_ai.db import execute
    kid = execute("INSERT INTO knowledge(topic,title,content) VALUES(?,?,?)", ("test", "roadmap", "v1"))
    first = upsert_knowledge_version(kid, "v1", "local://v1")
    second = upsert_knowledge_version(kid, "v2", "local://v2")
    assert second["version"] == 2
    conflict = execute("INSERT INTO knowledge_conflicts(claim_key,left_version_id,right_version_id) VALUES(?,?,?)", ("claim", first["id"], second["id"]))
    assert resolve_conflict(conflict, second["id"], "newer version") == conflict
    evidence_node("req:test", "requirement", "build")
    evidence_node("val:test", "validation", "pytest")
    evidence_edge("req:test", "validated-by", "val:test")
    assert trace(1, None, "req:test", "requirement", "build") > 0


def test_learning_trace_completion_and_benchmark():
    lesson_id = add_memory_lesson("known_failure", "retry after failed validation", "test")
    research_id = add_research_trace("req", "query", "source", "finding", "decision", "artifact", "pytest")
    assert lesson_id > 0 and research_id > 0
    report = completion_report("goal", ["req"], ["pytest"])
    assert report["complete"] is True
    result = benchmark_case("unit", "uppercase", "abc", "ABC", str.upper)
    assert result["passed"] is True
    assert benchmark_summary("unit")["passed"] >= 1


def test_personal_benchmark_suite_is_valid():
    from my_ai.personal_benchmark import validate_suite
    result = validate_suite()
    assert result["valid"] is True
    assert result["case_count"] >= 10


def test_model_management_and_selection_benchmark():
    management = model_management()
    assert management["models"]
    assert all("health" in item and "resource_fit" in item for item in management["models"])
    benchmark = benchmark_model_selection()
    assert benchmark["count"] == 3
    assert len(benchmark["cases"]) == 3


def test_personal_benchmark_runner_returns_case_results(monkeypatch):
    from my_ai import personal_benchmark
    monkeypatch.setattr(personal_benchmark, "load_suite", lambda: {"suites": {"retrieval": [{"name": "x", "input": "x", "expected": "knowledge"}]}})
    monkeypatch.setattr(personal_benchmark, "validate_suite", lambda: {"valid": True, "case_count": 1})
    monkeypatch.setattr(personal_benchmark, "recall", lambda query, limit: [{"hybrid_score": 1.0}])
    result = personal_benchmark.run_suite()
    assert result["valid"] is True
    assert result["passed"] == 1


def test_knowledge_version_restore_and_conflict_activation():
    from my_ai.db import execute, fetch_all
    from my_ai.roadmap_runtime import record_conflict, restore_knowledge_version, resolve_conflict, upsert_knowledge_version

    knowledge_id = execute("INSERT INTO knowledge(topic,title,content,verification_status,category) VALUES(?,?,?,?,?)", ("roadmap-test", "restore", "v1", "verified", "project_facts"))
    v1 = upsert_knowledge_version(knowledge_id, "v1", "source-1", 0.6)
    v2 = upsert_knowledge_version(knowledge_id, "v2", "source-2", 0.8)
    assert restore_knowledge_version(knowledge_id, v1["id"])["version"] == 1
    row = fetch_all("SELECT content FROM knowledge WHERE id=?", (knowledge_id,))[0]
    assert row["content"] == "v1"
    conflict_id = record_conflict("restore-claim", v1["id"], v2["id"])
    resolve_conflict(conflict_id, v2["id"], "selected newer source")
    row = fetch_all("SELECT content FROM knowledge WHERE id=?", (knowledge_id,))[0]
    assert row["content"] == "v2"
