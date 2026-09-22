from __future__ import annotations

from typing import Iterator, Sequence
import json

import httpx
import ipaddress
import urllib.parse
import time

from .config import settings
from .metrics import record_inference, record_error


class LLMError(RuntimeError):
    pass


HistoryMessage = dict[str, str]


class OllamaClient:
    def __init__(self, task: str | None = None) -> None:
        self.base_url = getattr(settings, "ollama_base_url", "http://127.0.0.1:11434").rstrip("/")
        if settings.offline_strict:
            host = urllib.parse.urlparse(self.base_url).hostname
            try:
                if not host or not ipaddress.ip_address(host).is_loopback:
                    raise ValueError
            except ValueError as exc:
                raise LLMError("Offline strict mode permits only loopback Ollama endpoints.") from exc
        self.default_model = getattr(settings, "ollama_model", "qwen2.5:7b")
        self.fallback_model = getattr(settings, "fallback_model", self.default_model)
        self.model = self._select_model(task)

    def _select_model(self, task: str | None) -> str:
        if not task:
            return self.default_model
        low = task.lower()
        if any(x in low for x in ("code","python","sql","debug","coding","patch","کد","برنامه","پروژه","رفع باگ")):
            return getattr(settings, "coding_model", self.default_model)
        if any(x in low for x in ("route","routing","classify","intent","simple","ساده","دسته")):
            return getattr(settings, "routing_model", self.default_model)
        return self.default_model

    def stream_chat(
        self,
        message: str,
        system: str | None = None,
        history: Sequence[HistoryMessage] | None = None,
    ) -> Iterator[str]:
        payload: dict[str, object] = {"model": self.model, "stream": True, "options": {"num_ctx": settings.ollama_num_ctx, "num_thread": settings.ollama_num_thread, "num_gpu": settings.ollama_num_gpu},
            "keep_alive": settings.ollama_keep_alive, "messages": []}
        messages = payload["messages"]
        assert isinstance(messages, list)
        if system:
            messages.append({"role": "system", "content": system})
        for item in history or ():
            if item.get("role") in {"user","assistant"} and isinstance(item.get("content"), str):
                messages.append({"role": item["role"], "content": item["content"]})
        messages.append({"role": "user", "content": message})
        yielded = False
        try:
            with httpx.stream("POST", f"{self.base_url}/api/chat", json=payload, timeout=300) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    data=json.loads(line)
                    chunk=data.get("message",{}).get("content")
                    if chunk:
                        yielded = True
                        yield str(chunk)
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            if not yielded and self.model != self.fallback_model:
                fallback_payload = dict(payload)
                fallback_payload["model"] = self.fallback_model
                try:
                    with httpx.stream("POST", f"{self.base_url}/api/chat", json=fallback_payload, timeout=300) as response:
                        response.raise_for_status()
                        self.model = self.fallback_model
                        for line in response.iter_lines():
                            if not line:
                                continue
                            data=json.loads(line)
                            chunk=data.get("message",{}).get("content")
                            if chunk:
                                yield str(chunk)
                        return
                except (httpx.HTTPError, json.JSONDecodeError) as fallback_exc:
                    raise LLMError(f"Ollama streaming request failed for primary and fallback models: {exc}; {fallback_exc}") from fallback_exc
            raise LLMError(f"Ollama streaming request failed: {exc}") from exc

    def chat(
        self,
        message: str,
        system: str | None = None,
        history: Sequence[HistoryMessage] | None = None,
    ) -> str:
        payload: dict[str, object] = {
            "model": self.model,
            "stream": False,
            "options": {"num_ctx": settings.ollama_num_ctx, "num_thread": settings.ollama_num_thread, "num_gpu": settings.ollama_num_gpu},
            "keep_alive": settings.ollama_keep_alive,
            "messages": [],
        }
        messages = payload["messages"]
        assert isinstance(messages, list)
        if system:
            messages.append({"role": "system", "content": system})
        for item in history or ():
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        started = time.perf_counter()
        try:
            response = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=300)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            record_error("ollama", self.model)
            if self.model != self.fallback_model:
                fallback_payload = dict(payload)
                fallback_payload["model"] = self.fallback_model
                try:
                    response = httpx.post(f"{self.base_url}/api/chat", json=fallback_payload, timeout=300)
                    response.raise_for_status()
                    self.model = self.fallback_model
                except httpx.HTTPError as fallback_exc:
                    raise LLMError(f"Ollama request failed for primary and fallback models: {exc}; {fallback_exc}") from fallback_exc
            else:
                raise LLMError(f"Ollama request failed: {exc}") from exc

        data = response.json()
        record_inference("ollama", self.model, time.perf_counter() - started, prompt_tokens=data.get("prompt_eval_count"), output_tokens=data.get("eval_count"))
        try:
            return str(data["message"]["content"])
        except (KeyError, TypeError) as exc:
            raise LLMError(f"Unexpected Ollama response: {data}") from exc


class OpenAICompatibleClient:
    """OpenAI Responses API backend, also usable with compatible gateways."""

    def __init__(self) -> None:
        if settings.offline_strict:
            raise LLMError("OpenAI is disabled in offline strict mode.")
        self.base_url = settings.openai_base_url
        self.model = settings.openai_model
        self.api_key = settings.openai_api_key
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

    def chat(
        self,
        message: str,
        system: str | None = None,
        history: Sequence[HistoryMessage] | None = None,
    ) -> str:
        input_items: list[dict[str, object]] = []
        for item in history or ():
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                input_items.append({"role": role, "content": content})
        input_items.append({"role": "user", "content": message})

        payload: dict[str, object] = {
            "model": self.model,
            "input": input_items,
        }
        if system:
            payload["instructions"] = system
        started = time.perf_counter()
        try:
            response = httpx.post(
                f"{self.base_url}/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=300,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            record_error("openai", self.model)
            raise LLMError(f"OpenAI-compatible request failed: {exc}") from exc

        data = response.json()
        usage = data.get("usage") if isinstance(data, dict) else {}
        record_inference("openai", self.model, time.perf_counter() - started, prompt_tokens=(usage or {}).get("input_tokens"), output_tokens=(usage or {}).get("output_tokens"))
        if isinstance(data.get("output_text"), str):
            return data["output_text"]
        chunks: list[str] = []
        for item in data.get("output", []) if isinstance(data, dict) else []:
            for content in item.get("content", []) if isinstance(item, dict) else []:
                if isinstance(content, dict) and isinstance(content.get("text"), str):
                    chunks.append(content["text"])
        if chunks:
            return "".join(chunks)
        raise LLMError(f"Unexpected OpenAI response: {data}")


def create_llm(task: str | None = None):
    provider = settings.llm_provider
    if provider in {"openai", "openai-compatible", "openai_compatible"}:
        return OpenAICompatibleClient()
    if provider == "auto":
        return OllamaClient(task=task)
    return OllamaClient(task=task)
