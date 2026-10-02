"""Configuration-first runtime adapters for mutable policies."""
from __future__ import annotations
from typing import Any
from .control_plane import get_record
from .settings_store import get_setting


def configured(namespace: str, name: str, default=None):
    item=get_record(namespace,name)
    if not item or not item.get("enabled"): return default
    return item.get("payload",default)


def behavior(name, default=None): return configured("agent.behavior",name,default)
def workflow(name, default=None): return configured("agent.workflow",name,default)
def tool(name, default=None): return configured("tools.catalog",name,default)
def memory_policy(name, default=None): return configured("memory.policy",name,default)
def research_policy(name, default=None): return configured("research.policy",name,default)
def security_policy(name, default=None): return configured("security.network",name,default)
def execution_profile(name, default=None): return configured("execution.profiles",name,default)
def integration(name, default=None): return configured("integrations.catalog",name,default)
def observability_policy(name, default=None): return configured("observability.dashboard",name,default)
def prompt(name, default=None): return configured("prompts.registry",name,default)
def policy(name, default=None): return configured("policies.registry",name,default)


class WorkflowEngine:
    """No-code workflow definition and deterministic execution."""
    def __init__(self, runner):
        self.runner=runner
    def run(self,name,context=None):
        definition=workflow(name,{})
        stages=definition.get("stages",[]) if isinstance(definition,dict) else []
        result=context or {}
        trace=[]
        for stage in stages:
            if stage.get("enabled",True) is False: continue
            started=self.runner.clock()
            value=self.runner.execute(stage,result)
            result=value if isinstance(value,dict) else {"value":value}
            trace.append({"stage":stage.get("name",""),"duration":self.runner.clock()-started,"result":result})
        return {"workflow":name,"result":result,"trace":trace}


class PolicyAwareTool:
    def __init__(self, name, execute):
        self.name=name; self.execute_fn=execute
    def run(self, payload, *, authorize):
        if not authorize(self.name,payload): raise PermissionError(f"tool denied: {self.name}")
        return self.execute_fn(payload)


def task_model(task_type, default=None):
    routes=configured("agent.routing","rules",{}).get("rules",[]) if configured("agent.routing","rules",{}) else []
    for rule in routes:
        if rule.get("task")==task_type and rule.get("model"): return rule["model"]
    return default
