from __future__ import annotations

import json
import time
from typing import Any, Iterator, Sequence

import httpx

from .provider import ProviderAdapterError, ProviderCapabilities, ProviderHealth, ProviderResponse, TokenUsage


HistoryMessage = dict[str, str]


class GenericHTTPProviderAdapter:
    """Protocol-neutral JSON/HTTP provider adapter.

    Request and response mappings are data-driven so an LLM with a non-OpenAI
    protocol can be registered without changing Agent/business code.
    """

    def __init__(
        self,
        *,
        name: str,
        endpoint: str,
        model: str,
        api_key: str = "",
        auth_header: str = "Authorization",
        auth_scheme: str = "Bearer",
        timeout: float = 60.0,
        capabilities: ProviderCapabilities | None = None,
        request_template: dict[str, Any] | None = None,
        response_path: str = "text",
        usage_paths: dict[str, str] | None = None,
        health_endpoint: str | None = None,
        stream_response_path: str = "delta",
        stream_format: str = "ndjson",
        stream_prefix: str = "data:",
        stream_done_value: str = "[DONE]",
    ) -> None:
        if not name.strip() or not endpoint.startswith(("http://", "https://")) or not model.strip():
            raise ValueError("name, HTTPS/HTTP endpoint and model are required")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.name = name.strip()
        self.endpoint = endpoint.rstrip("/")
        self.model = model.strip()
        self.api_key = api_key
        self.auth_header = auth_header
        self.auth_scheme = auth_scheme
        self.timeout = float(timeout)
        self.capabilities = capabilities or ProviderCapabilities(chat=True, streaming=False, structured_output=False)
        self.request_template = request_template or {}
        self.response_path = response_path
        self.usage_paths = usage_paths or {}
        self.health_endpoint = health_endpoint
        self.stream_response_path = stream_response_path
        self.stream_format = stream_format.lower().strip()
        self.stream_prefix = stream_prefix
        self.stream_done_value = stream_done_value

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            value = f"{self.auth_scheme} {self.api_key}".strip()
            headers[self.auth_header] = value
        return headers

    @staticmethod
    def _path_get(value: Any, path: str, default: Any = None) -> Any:
        current = value
        for part in str(path).split("."):
            if not part:
                continue
            if isinstance(current, dict):
                current = current.get(part, default)
            elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
                current = current[int(part)]
            else:
                return default
        return current

    def _payload(
        self,
        message: str,
        system: str | None,
        history: Sequence[HistoryMessage] | None,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        messages = [
            {"role": item.get("role"), "content": item.get("content")}
            for item in history or ()
            if item.get("role") in {"system", "user", "assistant"} and isinstance(item.get("content"), str)
        ]
        if system:
            messages.insert(0, {"role": "system", "content": system})
        messages.append({"role": "user", "content": message})
        payload = json.loads(json.dumps(self.request_template))
        payload.setdefault("model", self.model)
        payload.setdefault("messages", messages)
        if schema is not None:
            payload.setdefault("response_schema", schema)
        return payload

    def chat(self, message: str, *, system: str | None = None, history: list[dict[str, str]] | None = None) -> ProviderResponse:
        started = time.perf_counter()
        try:
            response = httpx.post(
                self.endpoint,
                headers=self._headers(),
                json=self._payload(message, system, history),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            text = self._path_get(data, self.response_path)
            if not isinstance(text, str):
                raise ProviderAdapterError(f"{self.name}: response path '{self.response_path}' did not contain text")
            usage = TokenUsage(
                input_tokens=self._path_get(data, self.usage_paths.get("input_tokens", ""), None),
                output_tokens=self._path_get(data, self.usage_paths.get("output_tokens", ""), None),
                total_tokens=self._path_get(data, self.usage_paths.get("total_tokens", ""), None),
            )
            return ProviderResponse(text=text, usage=usage, raw=data)
        except (httpx.HTTPError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ProviderAdapterError(f"{self.name}: request failed after {time.perf_counter() - started:.3f}s: {exc}") from exc

    def stream_chat(
        self,
        message: str,
        *,
        system: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> Iterator[str]:
        if not self.capabilities.streaming:
            raise ProviderAdapterError(f"{self.name}: streaming is not supported by this provider")
        if self.stream_format not in {"ndjson", "sse"}:
            raise ProviderAdapterError(f"{self.name}: unsupported stream format '{self.stream_format}'")
        started = time.perf_counter()
        try:
            with httpx.stream(
                "POST", self.endpoint, headers=self._headers(),
                json=self._payload(message, system, history), timeout=self.timeout,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    raw = line
                    if self.stream_format == "sse":
                        if not raw.startswith(self.stream_prefix):
                            continue
                        raw = raw[len(self.stream_prefix):].strip()
                    if raw == self.stream_done_value:
                        break
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError as exc:
                        raise ProviderAdapterError(f"{self.name}: invalid stream JSON") from exc
                    chunk = self._path_get(data, self.stream_response_path)
                    if isinstance(chunk, str) and chunk:
                        yield chunk
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise ProviderAdapterError(
                f"{self.name}: streaming request failed after {time.perf_counter() - started:.3f}s: {exc}"
            ) from exc

    def structured_chat_json(
        self,
        message: str,
        schema: dict[str, Any],
        *,
        system: str | None = None,
    ) -> dict[str, Any]:
        if not self.capabilities.structured_output:
            raise ProviderAdapterError(f"{self.name}: structured output is not supported")
        response = self.chat(message, system=system)
        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as exc:
            raise ProviderAdapterError(f"{self.name}: structured response is not valid JSON") from exc
        if not isinstance(data, dict):
            raise ProviderAdapterError(f"{self.name}: structured response must be an object")
        return data

    def health(self, *, timeout: float = 5.0) -> ProviderHealth:
        target = self.health_endpoint or self.endpoint
        started = time.perf_counter()
        try:
            response = httpx.get(target, headers=self._headers(), timeout=max(0.1, float(timeout)))
            response.raise_for_status()
            version = response.headers.get("x-provider-version") or response.headers.get("server")
            return ProviderHealth(
                provider=self.name,
                available=True,
                latency_ms=(time.perf_counter() - started) * 1000,
                version=version,
            )
        except (httpx.HTTPError, ValueError) as exc:
            return ProviderHealth(
                provider=self.name,
                available=False,
                latency_ms=(time.perf_counter() - started) * 1000,
                error=str(exc),
            )
