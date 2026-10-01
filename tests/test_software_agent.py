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


def test_mql4_validation_rejects_invalid_ea_market_price_and_auto_trade(tmp_path):
    from my_ai.software_validation import validate_generated_project

    (tmp_path / "MetaEA.mq4").write_text(
        "double Bid[]; double Ask[]; void OnTick(){ Bid=iClose(Symbol(),1,0); Ask=iClose(Symbol(),1,0); "
        "if(Bid>Ask) OrderSend(Symbol(),OP_BUY,0.1,Bid,3,0,0); }",
        encoding="utf-8",
    )
    defects = validate_generated_project(
        tmp_path,
        {"artifact_type": "Expert Advisor"},
        "MQL4",
    )
    assert any("arrays" in x for x in defects)
    assert any("trade strategy" in x for x in defects)
    assert any("user-controlled" in x for x in defects)


def test_mql4_indicator_rejects_trading_api(tmp_path):
    from my_ai.software_validation import validate_generated_project

    (tmp_path / "MyIndicator.mq4").write_text(
        "#property indicator_chart_window\nvoid OnCalculate(){}\nvoid x(){OrderSend(Symbol(),OP_BUY,0.1,Bid,3,0,0);}",
        encoding="utf-8",
    )
    defects = validate_generated_project(
        tmp_path,
        {"artifact_type": "MT4 custom indicator"},
        "MQL4",
    )
    assert any("custom indicator" in x.lower() and "ordersend" in x.lower() for x in defects)


def test_plan_recovers_explicit_language_when_planner_leaves_it_unknown(monkeypatch):
    from my_ai import software_agent

    class FakeLLM:
        def __init__(self):
            self.calls = 0

        def structured_chat_json(self, message, schema, system=None):
            self.calls += 1
            if self.calls == 1:
                return {
                    "goal": "Build a small program",
                    "artifact_type": "application",
                    "language": None,
                    "framework": None,
                    "requirements": ["read a text file"],
                    "tool_requirements": [],
                    "architecture": ["single process"],
                    "phases": ["build"],
                    "acceptance_criteria": ["program builds"],
                    "research_queries": [],
                    "validation": ["build"],
                    "constraints": [],
                    "ambiguities": [],
                }
            return {"explicit": True, "language": "C"}

    fake = FakeLLM()
    monkeypatch.setattr(software_agent, "create_llm", lambda task: fake)
    plan = software_agent._plan("Build a program in C that reads a text file")
    assert plan["language"] == "C"

def test_build_project_keeps_requirements_defined_when_semantic_validation_fails(monkeypatch, tmp_path):
    from my_ai import project_builder

    class FakeLLM:
        def chat(self, *args, **kwargs):
            return '{"files":{"main.txt":"generated"}}'

    monkeypatch.setattr(project_builder, "fetch_all", lambda *args: [])
    monkeypatch.setattr(project_builder, "create_project_workspace", lambda *args, **kwargs: tmp_path)
    monkeypatch.setattr(project_builder, "search_knowledge", lambda *args: [])
    monkeypatch.setattr(project_builder, "create_llm", lambda *args: FakeLLM())
    monkeypatch.setattr(project_builder, "validate_generated_project", lambda *args: ["semantic defect"])
    monkeypatch.setattr(project_builder, "execute", lambda *args: 1)
    monkeypatch.setattr(project_builder, "doctor", lambda *args, **kwargs: {})

    result = project_builder.build_project(
        "test project",
        language="Python",
        repair_attempts=0,
        tool_requirements=[{"capabilities": ["build"], "commands": {"build": ["python"]}}],
    )

    assert result["status"] == "build_failed"
    assert result["semantic_defects"] == ["semantic defect"]


def test_explicit_project_path_is_used_as_target_workspace(monkeypatch, tmp_path):
    from my_ai import project_builder

    monkeypatch.setattr(project_builder, "_recent_conversation_context", lambda goal: (goal, "Python", None))
    monkeypatch.setattr(project_builder, "search_knowledge", lambda *args: [])
    monkeypatch.setattr(project_builder, "resolve_projects_root", lambda path: tmp_path)
    monkeypatch.setattr(project_builder, "create_project_workspace", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not create a child workspace")))
    monkeypatch.setattr(project_builder, "_write_files", lambda workspace, files: [])
    monkeypatch.setattr(project_builder, "_run", lambda language, operation, workspace, timeout, requirements=None: {"passed": True, "operation": operation})
    monkeypatch.setattr(project_builder, "_artifact_files", lambda workspace: [])
    monkeypatch.setattr(project_builder, "doctor", lambda language, **kwargs: {"python": True})
    monkeypatch.setattr(project_builder, "execute", lambda *args: 1)

    class FakeLLM:
        def chat(self, *args, **kwargs):
            return '{"files":{"main.py":"print(1)"}}'

    monkeypatch.setattr(project_builder, "create_llm", lambda task: FakeLLM())
    result = project_builder.build_project("modify this project", project_path=str(tmp_path))

    assert result["project_path"] == str(tmp_path)


def test_failed_project_is_not_committed(monkeypatch, tmp_path):
    from my_ai import software_agent

    monkeypatch.setattr(software_agent, "_plan", lambda *args: {
        "goal": "test project", "artifact_type": "application", "language": "Python", "framework": None,
        "requirements": ["works"], "tool_requirements": [], "architecture": ["main"], "phases": ["build"],
        "acceptance_criteria": ["tests pass"], "research_queries": [], "validation": ["pytest"],
        "constraints": [], "ambiguities": [],
    })
    monkeypatch.setattr(software_agent, "_research", lambda *args: software_agent.ResearchBundle())
    monkeypatch.setattr(software_agent, "build_project", lambda *args, **kwargs: {
        "status": "build_failed", "language": "Python", "project_path": str(tmp_path),
        "files": [], "build": {"passed": False}, "tests": {"passed": False},
        "lint": {"passed": False}, "run": {"passed": False}, "semantic_defects": [],
    })
    result = software_agent.run_software_task("make it", project_path=str(tmp_path))
    assert result["completion"]["completed"] is False
    assert result["git"]["committed"] is False
    assert "not committed" in result["git"]["reason"]


def test_project_builder_performs_declared_runtime_validation(monkeypatch, tmp_path):
    from my_ai import project_builder

    monkeypatch.setattr(project_builder, "_recent_conversation_context", lambda goal: (goal, "Python", None))
    monkeypatch.setattr(project_builder, "search_knowledge", lambda *args: [])
    monkeypatch.setattr(project_builder, "resolve_projects_root", lambda path: tmp_path)
    monkeypatch.setattr(project_builder, "_write_files", lambda workspace, files: [])
    calls = []
    def fake_run(language, operation, workspace, timeout, requirements=None):
        calls.append(operation)
        return {"passed": True, "operation": operation}
    monkeypatch.setattr(project_builder, "_run", fake_run)
    monkeypatch.setattr(project_builder, "validate_generated_project", lambda *args: [])
    monkeypatch.setattr(project_builder, "_artifact_files", lambda workspace: [])
    monkeypatch.setattr(project_builder, "doctor", lambda language, **kwargs: {})
    monkeypatch.setattr(project_builder, "execute", lambda *args: 1)

    class FakeLLM:
        def chat(self, *args, **kwargs):
            return '{"files":{"main.py":"print(1)"}}'
    monkeypatch.setattr(project_builder, "create_llm", lambda task: FakeLLM())

    result = project_builder.build_project(
        "test project",
        language="Python",
        repair_attempts=0,
        tool_requirements=[{"executables": ["python"], "commands": {
            "build": ["python -m py_compile main.py"],
            "test": ["python -m pytest"],
            "lint": ["python -m compileall ."],
            "run": ["python main.py"],
        }}],
    )
    assert result["status"] == "built"
    assert calls == ["build", "test", "lint", "run"]


def test_acceptance_self_review_is_required_before_commit(monkeypatch, tmp_path):
    from my_ai import software_agent

    plan = {
        "goal": "test project", "artifact_type": "application", "language": "Python", "framework": None,
        "requirements": ["works"], "tool_requirements": [], "architecture": ["main"], "phases": ["build"],
        "acceptance_criteria": ["application starts"], "research_queries": [], "validation": ["run"],
        "constraints": [], "ambiguities": [],
    }
    monkeypatch.setattr(software_agent, "_plan", lambda *args: plan)
    monkeypatch.setattr(software_agent, "_research", lambda *args: software_agent.ResearchBundle())
    monkeypatch.setattr(software_agent, "build_project", lambda *args, **kwargs: {
        "status": "built", "language": "Python", "project_path": str(tmp_path),
        "files": ["main.py"], "build": {"passed": True}, "tests": {"passed": True},
        "lint": {"passed": True}, "run": {"passed": True}, "semantic_defects": [],
    })
    monkeypatch.setattr(software_agent, "_self_review", lambda *args: {
        "passed": False, "criteria": [], "defects": ["criterion not evidenced"], "notes": []
    })
    result = software_agent.run_software_task("make it", project_path=str(tmp_path))
    assert result["completion"]["self_review"] is False
    assert result["completion"]["completed"] is False
    assert result["git"]["committed"] is False


def test_acceptance_self_review_requires_every_criterion(monkeypatch, tmp_path):
    from my_ai import software_agent

    class FakeLLM:
        def structured_chat_json(self, message, schema, system=None):
            return {
                "passed": True,
                "criteria": [{"criterion": "first criterion", "passed": True, "evidence": "tests passed"}],
                "defects": [],
                "notes": [],
            }

    monkeypatch.setattr(software_agent, "create_llm", lambda task: FakeLLM())
    plan = {
        "goal": "test", "artifact_type": "application",
        "acceptance_criteria": ["first criterion", "second criterion"],
    }
    result = {"tests": {"passed": True}, "run": {"passed": True}, "semantic_defects": []}
    review = software_agent._self_review(plan, result, tmp_path)
    assert review["passed"] is False
    assert any("second criterion" in item for item in review["defects"])



def test_project_repair_includes_structured_failure_diagnosis(monkeypatch, tmp_path):
    from my_ai import project_builder

    class FakeLLM:
        def __init__(self):
            self.chat_calls = 0

        def chat(self, message, **kwargs):
            self.chat_calls += 1
            if self.chat_calls == 2:
                assert "STRUCTURED FAILURE DIAGNOSIS" in message
                assert "dependency" in message
            return '{"files":{"main.py":"print(1)"}}'

        def structured_chat_json(self, message, schema, system=None):
            assert "observable evidence" in message
            return {
                "category": "dependency",
                "cause": "missing dependency",
                "repair_strategy": "adjust the declared dependency and regenerate the artifact",
                "research_needed": False,
            }

    fake = FakeLLM()
    calls = []

    monkeypatch.setattr(project_builder, "_recent_conversation_context", lambda goal: (goal, "Python", None))
    monkeypatch.setattr(project_builder, "search_knowledge", lambda *args: [])
    monkeypatch.setattr(project_builder, "resolve_projects_root", lambda path: tmp_path)
    monkeypatch.setattr(project_builder, "_write_files", lambda workspace, files: [])
    monkeypatch.setattr(project_builder, "create_llm", lambda task: fake)
    monkeypatch.setattr(project_builder, "doctor", lambda *args, **kwargs: {})
    monkeypatch.setattr(project_builder, "_artifact_files", lambda workspace: [])
    monkeypatch.setattr(project_builder, "execute", lambda *args: 1)

    validation_calls = iter([["semantic defect"], []])
    monkeypatch.setattr(project_builder, "validate_generated_project", lambda *args: next(validation_calls))

    def fake_run(language, operation, workspace, timeout, requirements=None):
        calls.append(operation)
        return {"passed": True, "operation": operation}

    monkeypatch.setattr(project_builder, "_run", fake_run)

    result = project_builder.build_project(
        "test project",
        language="Python",
        project_path=str(tmp_path),
        repair_attempts=1,
        tool_requirements=[{"commands": {
            "build": ["python -m py_compile main.py"],
            "test": ["python -m pytest"],
            "lint": ["python -m compileall ."],
            "run": ["python main.py"],
        }}],
    )

    assert result["status"] == "built"
    assert result["failure_diagnosis"]["category"] == "dependency"
    assert calls == ["build", "test", "lint", "run"]


def test_failure_diagnosis_cannot_bypass_validation(monkeypatch, tmp_path):
    from my_ai import project_builder

    class FakeLLM:
        def chat(self, *args, **kwargs):
            return '{"files":{"main.py":"print(1)"}}'

        def structured_chat_json(self, *args, **kwargs):
            return {
                "category": "implementation",
                "cause": "looks repairable",
                "repair_strategy": "change the implementation",
                "research_needed": False,
            }

    monkeypatch.setattr(project_builder, "_recent_conversation_context", lambda goal: (goal, "Python", None))
    monkeypatch.setattr(project_builder, "search_knowledge", lambda *args: [])
    monkeypatch.setattr(project_builder, "resolve_projects_root", lambda path: tmp_path)
    monkeypatch.setattr(project_builder, "_write_files", lambda workspace, files: [])
    monkeypatch.setattr(project_builder, "create_llm", lambda task: FakeLLM())
    monkeypatch.setattr(project_builder, "validate_generated_project", lambda *args: ["still invalid"])
    monkeypatch.setattr(project_builder, "execute", lambda *args: 1)
    monkeypatch.setattr(project_builder, "doctor", lambda *args, **kwargs: {})
    monkeypatch.setattr(project_builder, "_artifact_files", lambda workspace: [])

    result = project_builder.build_project(
        "test project",
        language="Python",
        project_path=str(tmp_path),
        repair_attempts=0,
    )

    assert result["status"] == "build_failed"
    assert result["semantic_defects"] == ["still invalid"]
    assert result["failure_diagnosis"]["category"] == "implementation"


def test_workspace_cleanup_removes_generated_caches_without_touching_source_or_outputs(tmp_path):
    from my_ai import software_agent

    (tmp_path / "main.py").write_text("print('ok')", encoding="utf-8")
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "app.bin").write_text("artifact", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "main.cpython-313.pyc").write_bytes(b"cache")
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache" / "state").write_text("cache", encoding="utf-8")

    result = software_agent._cleanup_workspace(tmp_path)

    assert result["ok"] is True
    assert not (tmp_path / "__pycache__").exists()
    assert not (tmp_path / ".pytest_cache").exists()
    assert (tmp_path / "main.py").exists()
    assert (tmp_path / "dist" / "app.bin").exists()


def test_failure_diagnosis_allows_only_one_bounded_research_retry(monkeypatch, tmp_path):
    from my_ai import software_agent

    plan = {
        "goal": "build a small application",
        "artifact_type": "application",
        "language": "Python",
        "framework": None,
        "requirements": ["provide a usable application"],
        "tool_requirements": [],
        "architecture": ["simple application"],
        "phases": ["implement", "validate"],
        "acceptance_criteria": ["the application runs"],
        "research_queries": [],
        "validation": ["build", "test", "run"],
        "constraints": [],
        "ambiguities": [],
    }
    research_calls = []
    build_calls = []

    def fake_research(current_plan):
        research_calls.append(list(current_plan.get("research_queries") or []))
        return software_agent.ResearchBundle(
            sources=[{"url": f"https://example.test/{len(research_calls)}", "title": "source", "summary": "evidence"}],
            notes=["research completed"],
        )

    def fake_build(*args, **kwargs):
        build_calls.append(args[0])
        if len(build_calls) == 1:
            return {
                "status": "build_failed",
                "failure_diagnosis": {
                    "category": "dependency",
                    "cause": "missing dependency documentation",
                    "repair_strategy": "research the dependency requirements",
                    "research_needed": True,
                },
                "project_path": str(tmp_path),
                "build": {"passed": False},
                "tests": {"passed": False},
                "lint": {"passed": False},
                "run": {"passed": False},
                "semantic_defects": ["dependency unavailable"],
            }
        return {
            "status": "built",
            "project_path": str(tmp_path),
            "build": {"passed": True},
            "tests": {"passed": True},
            "lint": {"passed": True},
            "run": {"passed": True},
            "semantic_defects": [],
            "failure_diagnosis": {},
        }

    monkeypatch.setattr(software_agent, "_plan", lambda request, context: dict(plan))
    monkeypatch.setattr(software_agent, "_research", fake_research)
    monkeypatch.setattr(software_agent, "build_project", fake_build)
    monkeypatch.setattr(software_agent, "_self_review", lambda *args: {
        "passed": True,
        "criteria": [{"criterion": "the application runs", "passed": True, "evidence": "run passed"}],
        "defects": [],
        "notes": [],
    })
    monkeypatch.setattr(software_agent, "_cleanup_workspace", lambda workspace: {"ok": True, "removed": [], "count": 0})
    monkeypatch.setattr(software_agent, "_ensure_git_commit", lambda workspace, message: {"ok": True, "committed": True})

    result = software_agent.run_software_task("build an application", project_path=str(tmp_path))

    assert len(build_calls) == 2
    assert len(research_calls) == 2
    assert result["research_retry"] is True
    assert result["completion"]["completed"] is True
    assert research_calls[1] == ["missing dependency documentation"]



def test_self_review_collects_bounded_workspace_evidence(tmp_path):
    from my_ai import software_agent

    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("run the application\n", encoding="utf-8")
    evidence = software_agent._workspace_evidence(tmp_path)
    paths = {item["path"] for item in evidence}
    assert {"main.py", "README.md"}.issubset(paths)
    assert all(set(item) == {"path", "size", "content"} for item in evidence)
