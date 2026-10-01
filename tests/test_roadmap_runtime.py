import json

from my_ai.advanced_agent import Capability, OperationRisk, RuntimeMode, TaskProfile
from my_ai.roadmap_runtime import (
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
