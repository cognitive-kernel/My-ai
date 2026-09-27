from my_ai import api


def test_knowledge_management_ui_has_create_verify_audit_and_provenance():
    html = api.KNOWLEDGE_ADMIN_HTML
    assert "/memory/knowledge" in html
    assert "verification_status" in html
    assert "Audit" in html
    assert "source_url" in html
    assert "confidence" in html


def test_skill_engine_ui_exposes_independent_scores_and_evidence():
    html = api.SKILLS_ADMIN_HTML
    assert "knowledge_coverage_score" in html
    assert "verified_skill_score" in html
    assert "Evidence" in html
    assert "/skills/revalidate" in html
