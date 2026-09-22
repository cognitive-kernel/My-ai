import httpx

from my_ai.network import PinnedHTTPTransport


def test_pinned_transport_rewrites_host_and_preserves_sni(monkeypatch):
    seen = {}

    def fake_handle(self, request):
        seen["host"] = request.url.host
        seen["sni"] = request.extensions.get("sni_hostname")
        seen["header_host"] = request.headers["host"]
        return httpx.Response(200, request=request)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", fake_handle)
    monkeypatch.setattr("my_ai.network.resolve_public_ip", lambda hostname: "93.184.216.34")

    request = httpx.Request("GET", "https://example.com/path")
    response = PinnedHTTPTransport().handle_request(request)

    assert response.status_code == 200
    assert seen == {
        "host": "93.184.216.34",
        "sni": "example.com",
        "header_host": "example.com",
    }
