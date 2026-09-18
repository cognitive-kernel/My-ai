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
