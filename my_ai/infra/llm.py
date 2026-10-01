from __future__ import annotations

from typing import Iterator, Sequence
import json
import httpx
import ipaddress
import urllib.parse
import time
from .metrics import record_inference, record_error, record_route
from .resource_guard import limits, wait_until_available
from ..model_manager import ModelManager

def _settings():
    from .. import llm as legacy_llm
    return legacy_llm.settings


class LLMError(RuntimeError):
    pass
HistoryMessage = dict[str, str]

class OllamaClient:
    def __init__(self, task: str | None = None) -> None:
        self.base_url = getattr(_settings(), "ollama_base_url", "http://127.0.0.1:11434").rstrip("/")
        if getattr(_settings(), "offline_strict", False):
            host = urllib.parse.urlparse(self.base_url).hostname
            try:
                if not host or not ipaddress.ip_address(host).is_loopback: raise ValueError
            except ValueError as exc: raise LLMError("Offline strict mode permits only loopback Ollama endpoints.") from exc
        self.default_model = getattr(_settings(), "ollama_model", "qwen2.5:7b")
        self.fallback_model = getattr(_settings(), "fallback_model", self.default_model)
        self.model_manager = ModelManager()
        self.route_reason = "default"
        requested = self._select_model(task)
        self.model = self._preflight_model(requested, task)
    def _select_model(self, task: str | None) -> str:
        if not task:
            self.route_reason = "default"
            return self.default_model
        low = task.lower()
        if any(x in low for x in ("code","python","sql","debug","coding","patch","کد","برنامه","پروژه","رفع باگ")):
            self.route_reason = "coding_task"
            return getattr(_settings(), "coding_model", self.default_model)
        if any(x in low for x in ("route","routing","classify","intent","simple","ساده","دسته")):
            self.route_reason = "routing_task"
            return getattr(_settings(), "routing_model", self.default_model)
        if any(x in low for x in ("complex","reasoning","analysis","معماری","تحلیل","پیچیده")):
            self.route_reason = "complex_task"
            return self.default_model
        self.route_reason = "general_task"
        return self.default_model

    def _preflight_model(self, requested: str, task: str | None) -> str:
        status = self.model_manager.health(requested)
        if status.error is not None:
            record_route(task or "general", requested, "preflight_unknown")
            return requested
        if status.available:
            record_route(task or "general", requested, self.route_reason)
            return requested
        fallback = self.model_manager.choose_fallback(requested)
        if fallback:
            previous = self.route_reason
            self.route_reason = "preflight_fallback"
            record_route(task or "general", fallback, previous + ":fallback")
            return fallback
        record_route(task or "general", requested, self.route_reason + ":unavailable")
        return requested

    def health(self) -> dict[str, object]:
        status = self.model_manager.health(self.model)
        return {"provider": status.provider, "model": status.model, "available": status.available, "latency_ms": status.latency_ms, "error": status.error}

    def _options(self) -> dict[str, int]:
        cfg=limits(); return {"num_ctx":int(_settings().ollama_num_ctx),"num_thread":int(cfg["cpu_threads"]),"num_gpu":int(cfg["gpu_layers"])}
    def stream_chat(self,message:str,system:str|None=None,history:Sequence[HistoryMessage]|None=None,stop_event=None)->Iterator[str]:
        wait_until_available(stop_event, max_wait=_settings().resource_wait_seconds); messages: list[HistoryMessage] = []; payload={"model":self.model,"stream":True,"options":self._options(),"keep_alive":_settings().ollama_keep_alive,"messages":messages}
        if system: messages.append({"role":"system","content":system})
        for item in history or ():
            if item.get("role") in {"user","assistant"} and isinstance(item.get("content"),str): messages.append({"role":item["role"],"content":item["content"]})
        messages.append({"role":"user","content":message}); yielded=False; started=time.perf_counter()
        try:
            with httpx.stream("POST",f"{self.base_url}/api/chat",json=payload,timeout=300) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line: continue
                    data=json.loads(line); chunk=data.get("message",{}).get("content")
                    if chunk: yielded=True; yield str(chunk)
                    if data.get("done"): record_inference("ollama",self.model,time.perf_counter()-started,prompt_tokens=data.get("prompt_eval_count"),output_tokens=data.get("eval_count"))
        except (httpx.HTTPError,json.JSONDecodeError) as exc:
            record_error("ollama",self.model)
            if not yielded and self.model!=self.fallback_model:
                wait_until_available(stop_event, max_wait=_settings().resource_wait_seconds); fallback_payload=dict(payload); fallback_payload["model"]=self.fallback_model; fallback_payload["options"]=self._options()
                try:
                    with httpx.stream("POST",f"{self.base_url}/api/chat",json=fallback_payload,timeout=300) as response:
                        response.raise_for_status(); self.model=self.fallback_model
                        for line in response.iter_lines():
                            if not line: continue
                            data=json.loads(line); chunk=data.get("message",{}).get("content")
                            if chunk: yield str(chunk)
                            if data.get("done"): record_inference("ollama",self.model,time.perf_counter()-started,prompt_tokens=data.get("prompt_eval_count"),output_tokens=data.get("eval_count"))
                        return
                except (httpx.HTTPError,json.JSONDecodeError) as fallback_exc: raise LLMError(f"Ollama streaming request failed for primary and fallback models: {exc}; {fallback_exc}") from fallback_exc
            raise LLMError(f"Ollama streaming request failed: {exc}") from exc
    def structured_chat_json(self, message: str, schema: dict, system: str | None = None) -> dict:
        wait_until_available(None)
        messages = []
        if system: messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": message})
        payload = {"model": self.model, "stream": False, "format": schema, "options": self._options(), "keep_alive": _settings().ollama_keep_alive, "messages": messages}
        started = time.perf_counter()
        try:
            response = httpx.post(f"{self.base_url}/api/chat", json=payload, timeout=120); response.raise_for_status(); data = response.json()
            record_inference("ollama", self.model, time.perf_counter() - started, prompt_tokens=data.get("prompt_eval_count"), output_tokens=data.get("eval_count"))
            raw = ((data.get("message") or {}).get("content"))
            if not isinstance(raw, str): raise LLMError("Structured Ollama response has no message content.")
            parsed = json.loads(raw)
            if not isinstance(parsed, dict): raise LLMError("Structured Ollama response is not an object.")
            return parsed
        except (httpx.HTTPError, json.JSONDecodeError, LLMError) as exc:
            record_error("ollama", self.model); raise LLMError(f"Structured Ollama request failed: {exc}") from exc

    def chat(self,message:str,system:str|None=None,history:Sequence[HistoryMessage]|None=None,stop_event=None)->str:
        wait_until_available(stop_event); messages: list[HistoryMessage] = []; payload={"model":self.model,"stream":False,"options":self._options(),"keep_alive":_settings().ollama_keep_alive,"messages":messages}
        if system: messages.append({"role":"system","content":system})
        for item in history or ():
            role=item.get("role"); content=item.get("content")
            if role in {"user","assistant"} and isinstance(content,str) and content.strip(): messages.append({"role":role,"content":content})
        messages.append({"role":"user","content":message}); started=time.perf_counter()
        try:
            response=httpx.post(f"{self.base_url}/api/chat",json=payload,timeout=300); response.raise_for_status()
        except httpx.HTTPError as exc:
            record_error("ollama",self.model)
            if self.model!=self.fallback_model:
                wait_until_available(stop_event); fallback_payload=dict(payload); fallback_payload["model"]=self.fallback_model; fallback_payload["options"]=self._options()
                try: response=httpx.post(f"{self.base_url}/api/chat",json=fallback_payload,timeout=300); response.raise_for_status(); self.model=self.fallback_model
                except httpx.HTTPError as fallback_exc: raise LLMError(f"Ollama request failed for primary and fallback models: {exc}; {fallback_exc}") from fallback_exc
            else: raise LLMError(f"Ollama request failed: {exc}") from exc
        data=response.json(); record_inference("ollama",self.model,time.perf_counter()-started,prompt_tokens=data.get("prompt_eval_count"),output_tokens=data.get("eval_count"))
        try: return str(data["message"]["content"])
        except (KeyError,TypeError) as exc: raise LLMError(f"Unexpected Ollama response: {data}") from exc

class OpenAICompatibleClient:
    def __init__(self)->None:
        if getattr(_settings(),"offline_strict",False): raise LLMError("OpenAI is disabled in offline strict mode.")
        self.base_url=_settings().openai_base_url; self.model=_settings().openai_model; self.api_key=_settings().openai_api_key
        if not self.api_key: raise LLMError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
    def stream_chat(self,message:str,system:str|None=None,history:Sequence[HistoryMessage]|None=None)->Iterator[str]:
        input_items: list[HistoryMessage] = []
        for item in history or ():
            role=item.get("role"); content=item.get("content")
            if role in {"user","assistant"} and isinstance(content,str) and content.strip(): input_items.append({"role":role,"content":content})
        input_items.append({"role":"user","content":message}); payload={"model":self.model,"input":input_items,"stream":True}
        if system: payload["instructions"]=system
        started=time.perf_counter()
        try:
            with httpx.stream("POST",f"{self.base_url}/responses",headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"},json=payload,timeout=300) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data:"): continue
                    raw=line[5:].strip()
                    if raw=="[DONE]": continue
                    data=json.loads(raw)
                    if data.get("type")=="response.output_text.delta":
                        delta=data.get("delta")
                        if isinstance(delta,str) and delta: yield delta
                    elif data.get("type")=="response.completed":
                        usage=((data.get("response") or {}).get("usage") or {}); record_inference("openai",self.model,time.perf_counter()-started,prompt_tokens=usage.get("input_tokens"),output_tokens=usage.get("output_tokens"))
        except (httpx.HTTPError,json.JSONDecodeError) as exc: record_error("openai",self.model); raise LLMError(f"OpenAI-compatible streaming request failed: {exc}") from exc
    def chat(self,message:str,system:str|None=None,history:Sequence[HistoryMessage]|None=None)->str:
        input_items: list[HistoryMessage] = []
        for item in history or ():
            role=item.get("role"); content=item.get("content")
            if role in {"user","assistant"} and isinstance(content,str) and content.strip(): input_items.append({"role":role,"content":content})
        input_items.append({"role":"user","content":message}); payload={"model":self.model,"input":input_items}
        if system: payload["instructions"]=system
        started=time.perf_counter()
        try:
            response=httpx.post(f"{self.base_url}/responses",headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"},json=payload,timeout=300); response.raise_for_status()
        except httpx.HTTPError as exc: record_error("openai",self.model); raise LLMError(f"OpenAI-compatible request failed: {exc}") from exc
        data=response.json(); usage=data.get("usage") if isinstance(data,dict) else {}; record_inference("openai",self.model,time.perf_counter()-started,prompt_tokens=(usage or {}).get("input_tokens"),output_tokens=(usage or {}).get("output_tokens"))
        if isinstance(data.get("output_text"),str): return data["output_text"]
        chunks: list[str] = []
        for item in data.get("output",[]) if isinstance(data,dict) else []:
            for content in item.get("content",[]) if isinstance(item,dict) else []:
                if isinstance(content,dict) and isinstance(content.get("text"),str): chunks.append(content["text"])
        if chunks: return "".join(chunks)
        raise LLMError(f"Unexpected OpenAI response: {data}")

def create_llm(task:str|None=None):
    provider=_settings().llm_provider
    if provider in {"openai","openai-compatible","openai_compatible"}: return OpenAICompatibleClient()
    if provider=="auto":
        if _settings().openai_api_key and not getattr(_settings(),"offline_strict",False): return OpenAICompatibleClient()
        return OllamaClient(task=task)
    return OllamaClient(task=task)
