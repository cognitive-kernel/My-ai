import json
from pathlib import Path


def test_plan_is_semantic_and_contains_acceptance_criteria(monkeypatch):
    from my_ai import software_agent

    class FakeLLM:
        def structured_chat_json(self, message, schema, system=None):
            assert "trigger words" in message
            return {
                "goal": "A small playable point-eating game",
                "language": "Python",
                "framework": "pygame",
                "requirements": ["player movement", "collect points"],
                "architecture": ["game loop", "state model"],
                "phases": ["skeleton", "gameplay", "tests"],
                "acceptance_criteria": ["game starts", "player can collect a point"],
                "research_queries": ["pygame official getting started"],
                "validation": ["python compile", "pytest"],
            }

    monkeypatch.setattr(software_agent, "create_llm", lambda task: FakeLLM())
    plan = software_agent._plan("یه بازی نقطه خور کوچک بساز", "previous project context")
    assert plan["language"] == "Python"
    assert plan["acceptance_criteria"]
    assert plan["research_queries"]


def test_research_combines_local_knowledge_and_web_sources(monkeypatch):
    from my_ai import software_agent

    monkeypatch.setattr(software_agent, "search_knowledge", lambda *args: [
        {"title": "local Python", "source_url": "local://python", "content": "pytest"}
    ])

    class FakeWeb:
        def search(self, query, limit=6):
            return [{"title": "official docs", "url": "https://example.com/docs"}]

        def fetch(self, url):
            return "Official docs", "Use the documented API."

    monkeypatch.setattr(software_agent, "WebLearner", FakeWeb)
    monkeypatch.setattr(software_agent, "execute", lambda *args: None)
    bundle = software_agent._research({
        "goal": "test",
        "language": "Python",
        "framework": "",
        "research_queries": ["official Python docs"],
    })
    assert any(x["url"] == "local://python" for x in bundle.sources)
    assert any(x["url"] == "https://example.com/docs" for x in bundle.sources)


def test_run_software_task_requires_real_completion(monkeypatch, tmp_path):
    from my_ai import software_agent

    monkeypatch.setattr(software_agent, "_plan", lambda *args: {
        "goal": "test project", "language": "Python", "framework": None,
        "requirements": ["works"], "architecture": ["main"], "phases": ["build"],
        "acceptance_criteria": ["tests pass"], "research_queries": [], "validation": ["pytest"],
    })
    monkeypatch.setattr(software_agent, "_research", lambda *args: software_agent.ResearchBundle())
    monkeypatch.setattr(software_agent, "build_project", lambda *args, **kwargs: {
        "status": "build_failed", "language": "Python", "project_path": str(tmp_path),
        "files": [], "build": {"passed": False}, "tests": {"passed": False}, "lint": {"passed": False},
    })
    result = software_agent.run_software_task("make it", project_path=str(tmp_path))
    assert result["completion"]["completed"] is False
    assert result["status"] == "build_failed"


def test_git_commit_is_scoped_to_generated_workspace(tmp_path):
    from my_ai.software_agent import _ensure_git_commit
    (tmp_path / "README.md").write_text("generated", encoding="utf-8")
    result = _ensure_git_commit(tmp_path, "test: generated artifact")
    assert result["ok"] is True
    assert result["committed"] is True
    assert (tmp_path / ".git").exists()


def test_explicit_project_path_is_used_as_target_workspace(monkeypatch, tmp_path):
    from my_ai import project_builder

    monkeypatch.setattr(project_builder, "_recent_conversation_context", lambda goal: (goal, "Python", None))
    monkeypatch.setattr(project_builder, "search_knowledge", lambda *args: [])
    monkeypatch.setattr(project_builder, "resolve_projects_root", lambda path: tmp_path)
    monkeypatch.setattr(project_builder, "create_project_workspace", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not create a child workspace")))
    monkeypatch.setattr(project_builder, "_write_files", lambda workspace, files: [])
    monkeypatch.setattr(project_builder, "_run", lambda language, operation, workspace, timeout: {"passed": True, "operation": operation})
    monkeypatch.setattr(project_builder, "_artifact_files", lambda workspace: [])
    monkeypatch.setattr(project_builder, "doctor", lambda language: {"python": True})
    monkeypatch.setattr(project_builder, "execute", lambda *args: 1)

    class FakeLLM:
        def chat(self, *args, **kwargs):
            return '{"files":{"main.py":"print(1)"}}'

    monkeypatch.setattr(project_builder, "create_llm", lambda task: FakeLLM())
    result = project_builder.build_project("modify this project", project_path=str(tmp_path))

    assert result["project_path"] == str(tmp_path)
