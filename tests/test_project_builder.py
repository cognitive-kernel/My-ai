import json

def test_parse_project_files_and_path_safety():
    from my_ai.project_builder import _parse_files
    assert _parse_files(json.dumps({"files":{"src/main.py":"print(1)","README.md":"ok"}}))["src/main.py"]=="print(1)"
    try:
        _parse_files(json.dumps({"files":{"../bad.py":"x"}}))
        assert False
    except ValueError:
        pass
