from __future__ import annotations

import ipaddress
import socket

import httpx


def resolve_public_ip(hostname: str) -> str:
    """Resolve once and return a globally routable IP that can be pinned for the request."""
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except (OSError, ValueError) as exc:
        raise ValueError("Hostname could not be resolved.") from exc
    addresses: list[str] = []
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            continue
        if ip.is_global and not ip.is_multicast:
            addresses.append(str(ip))
    if not addresses:
        raise ValueError("Target must resolve only to globally routable addresses.")
    return addresses[0]


def assert_public_hostname(hostname: str) -> str:
    return resolve_public_ip(hostname)


class PinnedHTTPTransport(httpx.HTTPTransport):
    """HTTP transport that connects to the IP resolved for this request.

    The original hostname is preserved as the Host header and TLS SNI, so HTTPS
    certificate validation still applies to the requested hostname while the
    TCP connection cannot be redirected to a second DNS answer by a later
    resolver call.
    """

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        hostname = request.url.host
        ip = resolve_public_ip(hostname)
        extensions = dict(request.extensions)
        extensions["sni_hostname"] = hostname
        headers = request.headers.copy()
        if "host" not in headers:
            headers["Host"] = request.url.netloc.decode("ascii")
        pinned = httpx.Request(
            request.method,
            request.url.copy_with(host=ip),
            headers=headers,
            stream=request.stream,
            extensions=extensions,
        )
        return super().handle_request(pinned)


def pinned_client(**kwargs) -> httpx.Client:
    kwargs.setdefault("transport", PinnedHTTPTransport())
    return httpx.Client(**kwargs)
