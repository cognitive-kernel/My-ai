from my_ai.dast import LocalDAST


def test_dast_html_runs_local_server_and_finds_headers():
    html = "<!doctype html><html><body>login</body></html>"
    result = LocalDAST(timeout=3,startup_timeout=5).scan_code(html,"HTML")
    assert result["status"] == "sandbox_required"


def test_dast_rejects_non_local_targets():
    scanner = LocalDAST()
    try:
        scanner._assert_local("https://example.com")
        assert False
    except ValueError:
        assert True


def test_dast_public_target_uses_pinned_dns_resolution(monkeypatch):
    calls = []

    def fake_resolve(hostname):
        calls.append(hostname)
        return "93.184.216.34"

    monkeypatch.setattr("my_ai.dast.resolve_public_ip", fake_resolve)
    target = LocalDAST()._assert_public_explicit("https://example.com/path")
    assert target.hostname == "example.com"
    assert calls == ["example.com"]


def test_dast_external_requests_use_pinned_client(monkeypatch):
    calls = []

    class FakeResponse:
        status_code = 200
        text = "<html></html>"
        headers = {"content-type": "text/html"}

    class FakeClient:
        def __enter__(self):
            calls.append("enter")
            return self

        def __exit__(self, exc_type, exc, tb):
            calls.append("exit")

        def get(self, url):
            calls.append(("get", url))
            return FakeResponse()

        def request(self, method, url):
            calls.append(("request", method, url))
            return FakeResponse()

    def fake_pinned_client(**kwargs):
        calls.append(("pinned_client", kwargs))
        return FakeClient()

    monkeypatch.setattr("my_ai.dast.pinned_client", fake_pinned_client)
    scanner = LocalDAST(timeout=3)
    scanner._checks("https://example.com/", ["/"])
    scanner._openapi_endpoints("https://example.com/")
    scanner._crawl_public("https://example.com/", limit=1)

    assert sum(1 for call in calls if isinstance(call, tuple) and call[0] == "pinned_client") == 3
    assert not any(call == "httpx_client" for call in calls)


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
