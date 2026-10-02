"""Configuration-driven model routing and fallback selection."""
from __future__ import annotations
import time
from typing import Any
from .provider_catalog import list_providers, list_models
from .control_plane import get_record


class ModelRouter:
    def __init__(self):
        self.last_decisions=[]

    def _rules(self):
        item=get_record("agent.routing","rules") or {}
        return item.get("payload",{}).get("rules",[]) if isinstance(item,dict) else []

    def select(self, task_type: str, *, required_capabilities=(), max_cost=None, max_latency=None) -> dict[str,Any]:
        providers={p["id"]:p for p in list_providers(include_disabled=False)}
        models=[m for m in list_models(include_disabled=False) if m["provider_id"] in providers]
        required=set(required_capabilities)
        candidates=[]
        for m in models:
            caps=set((providers[m["provider_id"]].get("capabilities") or {}).keys()) | set(m.get("tasks") or [])
            if required and not required<=caps: continue
            limits=m.get("limits") or {}
            cost=float(limits.get("cost",0))
            latency=float(limits.get("latency_ms",0))
            if max_cost is not None and cost>max_cost: continue
            if max_latency is not None and latency>max_latency: continue
            candidates.append((m,providers[m["provider_id"]],cost,latency))
        rules=self._rules()
        for rule in rules:
            if rule.get("task") not in (None,task_type): continue
            preferred=set(rule.get("models",[]))
            for m,p,c,l in candidates:
                if m["model_id"] in preferred:
                    return self._remember(task_type,m,p,"rule")
        if not candidates: raise LookupError(f"No model available for task {task_type}")
        candidates.sort(key=lambda x:(x[2],x[3],x[0].get("priority",100)))
        m,p,_,_=candidates[0]
        return self._remember(task_type,m,p,"automatic")

    def fallback_chain(self, task_type: str) -> list[str]:
        item=get_record("agent.routing","fallback") or {}
        chain=item.get("payload",{}).get(task_type) or item.get("payload",{}).get("default",[])
        return [str(x) for x in chain]

    def _remember(self,task,m,p,reason):
        decision={"task":task,"provider":p["name"],"model":m["model_id"],"reason":reason,"at":time.time()}
        self.last_decisions.append(decision); self.last_decisions=self.last_decisions[-100:]
        return decision
