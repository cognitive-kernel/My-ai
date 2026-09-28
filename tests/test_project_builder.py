import json

def test_parse_project_files_and_path_safety():
    from my_ai.project_builder import _parse_files
    assert _parse_files(json.dumps({"files":{"src/main.py":"print(1)"}}))["src/main.py"]=="print(1)"
    try:
        _parse_files(json.dumps({"files":{"../bad.py":"x"}}))
        assert False
    except ValueError:
        pass

def test_project_builder_multi_file(monkeypatch,tmp_path):
    from my_ai import project_builder, project_workspace
    root=tmp_path/"projects"; root.mkdir()
    monkeypatch.setattr(project_workspace,"PROJECTS_ROOT",root)
    monkeypatch.setattr(project_builder,"create_project_workspace",lambda goal: project_workspace.create_project_workspace(goal))
    monkeypatch.setattr(project_builder,"_run",lambda *a,**k: {"passed":True,"return_code":0,"output":"ok","error":""})
    monkeypatch.setattr(project_builder,"search_knowledge",lambda *a,**k: [])
    monkeypatch.setattr(project_builder,"execute",lambda *a,**k: 1)
    class FakeLLM:
        def chat(self,*a,**k):
            return json.dumps({"files":{"pyproject.toml":"[project]","main.py":"print(1)","tests/test_main.py":"def test_ok(): assert True"}})
    monkeypatch.setattr(project_builder,"create_llm",lambda *a,**k: FakeLLM())
    monkeypatch.setattr(project_builder,"doctor",lambda lang: {"Python":{}})
    result=project_builder.build_project("demo","Python",repair_attempts=0)
    assert result["status"]=="built" and result["file_count"]==3
