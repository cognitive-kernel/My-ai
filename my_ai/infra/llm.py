from __future__ import annotations

from typing import Iterator, Sequence
import json
import httpx
import ipaddress
import urllib.parse
import time
from .metrics import record_inference, record_error, record_route
from .resource_guard import limits, wait_until_available
from .provider import ProviderCapabilities
from .generic_provider import GenericHTTPProviderAdapter
from ..model_manager import ModelManager
from ..provider_catalog import get_provider_runtime_config
from ..settings_store import get_setting

def _settings():
    from .. import llm as legacy_llm
    return legacy_llm.settings

class LLMError(RuntimeError):
    pass

def _runtime_setting(key: str, fallback):
    try:
        return get_setting(key, fallback)
    except Exception:
        return fallback
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
        self.fallback_chain = self.model_manager.fallback_chain(self.default_model)
        self.route_reason = "default"
        self.model = self._preflight_model(self._select_model(task), task)

    def _retry_attempts(self) -> int:
        return max(1, min(5, int(_runtime_setting("llm.retry_attempts", getattr(_settings(), "llm_model_retry_attempts", getattr(_settings(), "llm_retry_attempts", 2))))))
    def _timeout(self) -> float:
        return max(1.0, float(_runtime_setting("llm.timeout_seconds", getattr(_settings(), "llm_model_timeout_seconds", getattr(_settings(), "llm_timeout_seconds", 300)))))
    def _backoff(self, attempt: int) -> None:
        delay=max(0.0,min(10.0,float(getattr(_settings(),"llm_model_retry_backoff_seconds",getattr(_settings(),"llm_retry_backoff_seconds",0.5)))))
        if delay: time.sleep(delay*(2**max(0,attempt-1)))
    def _post_json(self,url:str,payload:dict,*,headers:dict|None=None)->httpx.Response:
        response=httpx.post(url,json=payload,headers=headers,timeout=self._timeout()); response.raise_for_status(); return response

    def _select_model(self, task: str | None) -> str:
        if not task:
            self.route_reason = "default"
            return self.default_model
        low = task.lower()
        task_kind = "general"
        if any(x in low for x in ("code","python","sql","debug","coding","patch","کد","برنامه","پروژه","رفع باگ")):
            task_kind = "coding"
        elif any(x in low for x in ("route","routing","classify","intent","simple","ساده","دسته")):
            task_kind = "routing"
        elif any(x in low for x in ("complex","reasoning","analysis","معماری","تحلیل","پیچیده")):
            task_kind = "reasoning"
        selected = self.model_manager.select_for_task(task_kind)
        if selected:
            self.route_reason = "catalog_capability"
            return selected
        self.route_reason = task_kind + "_fallback"
        return getattr(_settings(), f"{task_kind}_model", self.default_model) if task_kind in {"coding","routing"} else self.default_model

    def _preflight_model(self, requested: str, task: str | None) -> str:
        status=self.model_manager.health(requested)
        if status.error is not None: record_route(task or "general",requested,"preflight_unknown"); return requested
        if status.available: record_route(task or "general",requested,self.route_reason); return requested
        fallback=self.model_manager.choose_fallback(requested)
        if fallback:
            previous=self.route_reason; self.route_reason="preflight_fallback"; record_route(task or "general",fallback,previous+":fallback"); return fallback
        record_route(task or "general",requested,self.route_reason+":unavailable"); return requested

    def health(self)->dict[str,object]:
        status=self.model_manager.health(self.model); return {"provider":status.provider,"model":status.model,"available":status.available,"latency_ms":status.latency_ms,"error":status.error}
    def _options(self)->dict[str,int]:
        cfg=limits(); return {"num_ctx":int(_settings().ollama_num_ctx),"num_thread":int(cfg["cpu_threads"]),"num_gpu":int(cfg["gpu_layers"])}

    def stream_chat(self,message:str,system:str|None=None,history:Sequence[HistoryMessage]|None=None,stop_event=None)->Iterator[str]:
        wait_until_available(stop_event,max_wait=_settings().resource_wait_seconds)
        messages=[]
        if system: messages.append({"role":"system","content":system})
        for item in history or ():
            if item.get("role") in {"user","assistant"} and isinstance(item.get("content"),str): messages.append({"role":item["role"],"content":item["content"]})
        messages.append({"role":"user","content":message}); candidates=[self.model]+[m for m in self.fallback_chain if m!=self.model]; errors=[]; started=time.perf_counter()
        for candidate in candidates:
            payload={"model":candidate,"stream":True,"options":self._options(),"keep_alive":_settings().ollama_keep_alive,"messages":messages}
            for attempt in range(1,self._retry_attempts()+1):
                yielded=False
                try:
                    with httpx.stream("POST",f"{self.base_url}/api/chat",json=payload,timeout=self._timeout()) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            if not line: continue
                            data=json.loads(line); chunk=data.get("message",{}).get("content")
                            if chunk: yielded=True; yield str(chunk)
                            if data.get("done"): record_inference("ollama",candidate,time.perf_counter()-started,prompt_tokens=data.get("prompt_eval_count"),output_tokens=data.get("eval_count"))
                    self.model=candidate; return
                except (httpx.HTTPError,json.JSONDecodeError) as exc:
                    record_error("ollama",candidate); errors.append(f"{candidate} attempt {attempt}: {exc}")
                    record_route(messages[-1]["content"], candidate, f"failure_attempt_{attempt}")
                    if yielded or attempt>=self._retry_attempts(): break
                    self._backoff(attempt)
        raise LLMError("Ollama streaming request failed for all model candidates: "+" | ".join(errors))

    def structured_chat_json(self,message:str,schema:dict,system:str|None=None)->dict:
        wait_until_available(None); messages=[]
        if system: messages.append({"role":"system","content":system})
        messages.append({"role":"user","content":message}); payload={"model":self.model,"stream":False,"format":schema,"options":self._options(),"keep_alive":_settings().ollama_keep_alive,"messages":messages}; started=time.perf_counter(); errors=[]
        for candidate in [self.model]+[m for m in self.fallback_chain if m!=self.model]:
            for attempt in range(1,self._retry_attempts()+1):
                try:
                    attempt_payload=dict(payload); attempt_payload["model"]=candidate; response=self._post_json(f"{self.base_url}/api/chat",attempt_payload); data=response.json(); raw=((data.get("message") or {}).get("content"))
                    if not isinstance(raw,str): raise LLMError("Structured Ollama response has no message content.")
                    parsed=json.loads(raw)
                    if not isinstance(parsed,dict): raise LLMError("Structured Ollama response is not an object.")
                    record_inference("ollama",candidate,time.perf_counter()-started,prompt_tokens=data.get("prompt_eval_count"),output_tokens=data.get("eval_count")); self.model=candidate; return parsed
                except (httpx.HTTPError,json.JSONDecodeError,LLMError) as exc:
                    errors.append(f"{candidate} attempt {attempt}: {exc}"); record_error("ollama",candidate); record_route(message, candidate, f"failure_attempt_{attempt}")
                    if attempt<self._retry_attempts(): self._backoff(attempt)
        raise LLMError("Structured Ollama request failed for all model candidates: "+" | ".join(errors))

    def chat(self,message:str,system:str|None=None,history:Sequence[HistoryMessage]|None=None,stop_event=None)->str:
        wait_until_available(stop_event); messages=[]
        if system: messages.append({"role":"system","content":system})
        for item in history or ():
            role=item.get("role"); content=item.get("content")
            if role in {"user","assistant"} and isinstance(content,str) and content.strip(): messages.append({"role":role,"content":content})
        messages.append({"role":"user","content":message}); started=time.perf_counter(); errors=[]
        for candidate in [self.model]+[m for m in self.fallback_chain if m!=self.model]:
            payload={"model":candidate,"stream":False,"options":self._options(),"keep_alive":_settings().ollama_keep_alive,"messages":messages}
            for attempt in range(1,self._retry_attempts()+1):
                try:
                    response=self._post_json(f"{self.base_url}/api/chat",payload); data=response.json(); content=data["message"]["content"]
                    record_inference("ollama",candidate,time.perf_counter()-started,prompt_tokens=data.get("prompt_eval_count"),output_tokens=data.get("eval_count")); self.model=candidate; return str(content)
                except (httpx.HTTPError,KeyError,TypeError,LLMError) as exc:
                    errors.append(f"{candidate} attempt {attempt}: {exc}"); record_error("ollama",candidate); record_route(message, candidate, f"failure_attempt_{attempt}")
                    if attempt<self._retry_attempts(): self._backoff(attempt)
        raise LLMError("Ollama request failed for all model candidates: "+" | ".join(errors))

class OpenAICompatibleClient:
    def __init__(self, *, base_url: str | None = None, model: str | None = None, api_key: str | None = None, provider_name: str = "openai"):
        if getattr(_settings(),"offline_strict",False): raise LLMError("OpenAI-compatible providers are disabled in offline strict mode.")
        self.base_url=(base_url or _settings().openai_base_url).rstrip("/")
        self.model=model or _settings().openai_model
        self.api_key=api_key or _settings().openai_api_key
        self.provider_name=provider_name
        if not self.base_url or not self.base_url.startswith(("http://","https://")): raise LLMError(f"{provider_name} base URL is required")
        if not self.model: raise LLMError(f"{provider_name} model ID is required")
        if not self.api_key: raise LLMError(f"{provider_name} API key is required")
    def _retry_attempts(self) -> int:
        return max(1, min(5, int(_runtime_setting("llm.retry_attempts", getattr(_settings(), "llm_retry_attempts", 2)))))

    def _timeout(self) -> float:
        return max(1.0, float(_runtime_setting("llm.timeout_seconds", getattr(_settings(), "llm_timeout_seconds", 300))))

    def _backoff(self, attempt: int) -> None:
        delay=max(0.0,min(10.0,float(getattr(_settings(),"llm_retry_backoff_seconds",0.5))))
        if delay: time.sleep(delay*(2**max(0,attempt-1)))

    def stream_chat(self,message:str,system:str|None=None,history:Sequence[HistoryMessage]|None=None)->Iterator[str]:
        items=[{"role":i.get("role"),"content":i.get("content")} for i in history or () if i.get("role") in {"user","assistant"} and isinstance(i.get("content"),str)]; items.append({"role":"user","content":message}); payload={"model":self.model,"input":items,"stream":True}; started=time.perf_counter(); errors=[]
        for attempt in range(1,self._retry_attempts()+1):
            try:
                with httpx.stream("POST",f"{self.base_url}/responses",headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"},json=payload,timeout=self._timeout()) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line or not line.startswith("data:"): continue
                        raw=line[5:].strip()
                        if raw=="[DONE]": continue
                        data=json.loads(raw)
                        if data.get("type")=="response.output_text.delta" and isinstance(data.get("delta"),str): yield data["delta"]
                        elif data.get("type")=="response.completed":
                            usage=((data.get("response") or {}).get("usage") or {}); record_inference(self.provider_name,self.model,time.perf_counter()-started,prompt_tokens=usage.get("input_tokens"),output_tokens=usage.get("output_tokens"))
                return
            except (httpx.HTTPError,json.JSONDecodeError) as exc:
                errors.append(f"attempt {attempt}: {exc}"); record_error(self.provider_name,self.model); record_route(message,self.model,f"failure_attempt_{attempt}")
                if attempt < self._retry_attempts(): self._backoff(attempt)
        raise LLMError("OpenAI-compatible streaming request failed: "+" | ".join(errors))
    def structured_chat_json(self,message:str,schema:dict,system:str|None=None)->dict:
        payload={"model":self.model,"input":[{"role":"user","content":message}],"text":{"format":{"type":"json_schema","name":"my_ai_structured","schema":schema,"strict":True}}}
        if system:
            payload["instructions"]=system
        try:
            response=httpx.post(f"{self.base_url}/responses",headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"},json=payload,timeout=self._timeout())
            response.raise_for_status()
            data=response.json()
            raw=data.get("output_text")
            if not isinstance(raw,str):
                chunks=[c.get("text") for i in data.get("output",[]) if isinstance(i,dict) for c in i.get("content",[]) if isinstance(c,dict) and isinstance(c.get("text"),str)]
                raw="".join(chunks)
            parsed=json.loads(raw)
            if not isinstance(parsed,dict):
                raise LLMError("Structured OpenAI-compatible response is not an object.")
            return parsed
        except (httpx.HTTPError,json.JSONDecodeError,TypeError,LLMError) as exc:
            record_error(self.provider_name,self.model)
            raise LLMError(f"Structured {self.provider_name} request failed: {exc}") from exc

    def health(self, *, timeout: float = 5.0):
        from .provider import ProviderHealth
        started=time.perf_counter()
        try:
            response=httpx.get(f"{self.base_url}/models",headers={"Authorization":f"Bearer {self.api_key}"},timeout=timeout)
            response.raise_for_status()
            return ProviderHealth(self.provider_name,True,(time.perf_counter()-started)*1000)
        except httpx.HTTPError as exc:
            return ProviderHealth(self.provider_name,False,(time.perf_counter()-started)*1000,error=str(exc))

    def chat(self,message:str,system:str|None=None,history:Sequence[HistoryMessage]|None=None)->str:
        items=[{"role":i.get("role"),"content":i.get("content")} for i in history or () if i.get("role") in {"user","assistant"} and isinstance(i.get("content"),str)]; items.append({"role":"user","content":message}); payload={"model":self.model,"input":items}; payload.update({"instructions":system} if system else {}); started=time.perf_counter(); errors=[]
        for attempt in range(1,self._retry_attempts()+1):
            try:
                response=httpx.post(f"{self.base_url}/responses",headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"},json=payload,timeout=self._timeout()); response.raise_for_status()
                data=response.json(); usage=data.get("usage") if isinstance(data,dict) else {}; record_inference(self.provider_name,self.model,time.perf_counter()-started,prompt_tokens=(usage or {}).get("input_tokens"),output_tokens=(usage or {}).get("output_tokens"))
                if isinstance(data.get("output_text"),str): return data["output_text"]
                chunks=[c["text"] for i in data.get("output",[]) if isinstance(i,dict) for c in i.get("content",[]) if isinstance(c,dict) and isinstance(c.get("text"),str)]
                if chunks: return "".join(chunks)
                raise LLMError(f"Unexpected OpenAI response: {data}")
            except (httpx.HTTPError,LLMError,json.JSONDecodeError) as exc:
                errors.append(f"attempt {attempt}: {exc}"); record_error(self.provider_name,self.model); record_route(message,self.model,f"failure_attempt_{attempt}")
                if attempt < self._retry_attempts(): self._backoff(attempt)
        raise LLMError("OpenAI-compatible request failed: "+" | ".join(errors))

def _provider_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register("ollama", lambda task=None: OllamaClient(task=task))
    registry.register("openai-compatible", lambda: OpenAICompatibleClient())
    registry.register(
        "custom-openai-compatible",
        lambda: OpenAICompatibleClient(
            base_url=str(_runtime_setting("llm.custom.base_url", "")),
            model=str(_runtime_setting("llm.custom.model", "")),
            api_key=str(_runtime_setting("llm.custom.api_key", "")),
            provider_name="custom-openai-compatible",
        ),
    )
    try:
        from ..provider_catalog import list_providers, list_models
        providers = list_providers(include_disabled=False)
        models = list_models(include_disabled=False)
        model_by_provider = {}
        for item in models:
            model_by_provider.setdefault(int(item["provider_id"]), []).append(item)
        for provider in providers:
            protocol = str(provider.get("protocol", "")).strip().lower()
            if protocol in {"openai-compatible", "openai", "ollama"}:
                continue
            candidates = model_by_provider.get(int(provider["id"]), [])
            if not candidates:
                continue
            model = candidates[0]
            capabilities = provider.get("capabilities") or {}
            caps = ProviderCapabilities(
                chat=bool(capabilities.get("chat", True)),
                streaming=bool(capabilities.get("streaming", False)),
                structured_output=bool(capabilities.get("structured_output", False)),
                embeddings=bool(capabilities.get("embeddings", False)),
                reasoning=bool(capabilities.get("reasoning", False)),
                health_check=bool(capabilities.get("health_check", True)),
            )
            name = str(provider["name"])
            runtime = get_provider_runtime_config(int(provider['id']))
            registry.register(
                name,
                lambda p=provider, m=model, c=caps, rt=runtime: GenericHTTPProviderAdapter(
                    name=str(p['name']), endpoint=str(p['endpoint']), model=str(m['model_id']),
                    api_key=str(rt.get('api_key', '')),
                    auth_header=str(rt.get('capabilities', {}).get('auth_header', 'Authorization')),
                    auth_scheme=str(rt.get('capabilities', {}).get('auth_scheme', 'Bearer')),
                    timeout=float(p.get('timeout_seconds') or 30), capabilities=c,
                    request_template=dict(rt.get('capabilities', {}).get('request_template') or {}),
                    response_path=str(rt.get('capabilities', {}).get('response_path', 'text')),
                    usage_paths=dict(rt.get('capabilities', {}).get('usage_paths') or {}),
                    health_endpoint=rt.get('capabilities', {}).get('health_endpoint'),
                    stream_response_path=str(rt.get('capabilities', {}).get('stream_response_path', 'delta')),
                    stream_format=str(rt.get('capabilities', {}).get('stream_format', 'ndjson')),
                    stream_prefix=str(rt.get('capabilities', {}).get('stream_prefix', 'data:')),
                    stream_done_value=str(rt.get('capabilities', {}).get('stream_done_value', '[DONE]')),
                ),
            )
    except Exception:
        # Optional catalog providers must not prevent built-in providers from starting.
        pass
    return registry


def create_llm(task: str | None = None):
    provider = str(_runtime_setting("llm.provider", _settings().llm_provider))
    if provider in {"openai", "openai-compatible", "openai_compatible"}:
        provider = "openai-compatible"
    if provider == "auto":
        provider = "openai-compatible" if _settings().openai_api_key and not getattr(_settings(), "offline_strict", False) else "ollama"
    try:
        return _provider_registry().create(provider, task=task) if provider == "ollama" else _provider_registry().create(provider)
    except Exception as exc:
        if isinstance(exc, LLMError):
            raise
        raise LLMError(str(exc)) from exc
