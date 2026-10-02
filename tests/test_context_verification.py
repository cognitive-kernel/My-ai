from my_ai.infra.context_engine import ContextItem, assemble_context, render_context
from my_ai.infra.verification import verify


def test_context_engine_prioritizes_and_respects_budget():
    items = [
        ContextItem("low", source="low", priority=1),
        ContextItem("high", source="high", priority=10),
        ContextItem("medium", source="medium", priority=5),
    ]
    selected = assemble_context(items, max_chars=10)
    assert selected[0].source == "high"
    assert len(render_context(selected)) > 0


def test_context_engine_can_require_source_outside_budget():
    selected = assemble_context(
        [ContextItem("123456789", source="required", priority=0), ContextItem("abc", source="other", priority=1)],
        max_chars=3,
        required_sources={"required"},
    )
    assert [item.source for item in selected] == ["other", "required"]


def test_verification_collects_evidence_and_confidence():
    result = verify([("unit", lambda: True), ("regression", lambda: False)], require_all=False)
    assert result.passed is True
    assert result.confidence == 0.5
    assert [item.kind for item in result.evidence] == ["unit", "regression"]
