from my_ai.dast import LocalDAST

def test_dast_html_runs_local_server_and_finds_headers():
    html = "<!doctype html><html><body>login</body></html>"
    result = LocalDAST(timeout=3,startup_timeout=5).scan_code(html,"HTML")
    assert result["status"] == "completed"
    assert result["target"].startswith("http://127.0.0.1:")
    rules = {f["title"] for f in result["findings"]}
    assert "Missing Content-Security-Policy" in rules
    assert "Missing X-Content-Type-Options" in rules

def test_dast_rejects_non_local_targets():
    scanner = LocalDAST()
    try:
        scanner._assert_local("https://example.com")
        assert False
    except ValueError:
        assert True



def test_executor_container_flags(monkeypatch, tmp_path):
    from my_ai import executor
    calls=[]
    class R:
        stdout="ok"; stderr=""; returncode=0
    monkeypatch.setattr(executor.subprocess,"run",lambda cmd,**kwargs:(calls.append(cmd) or R()))
    result=executor._run_container("print(1)")
    assert result.sandbox_mode=="container"
    cmd=calls[0]
    assert "--network" in cmd and "none" in cmd
    assert "--read-only" in cmd
    assert "--cap-drop" in cmd and "ALL" in cmd
    assert "--security-opt" in cmd and "no-new-privileges" in cmd
    assert "--pids-limit" in cmd
