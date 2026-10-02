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

def learning_source(name, default=None): return configured("learning.sources",name,default)
def learning_policy(name, default=None): return configured("learning.policy",name,default)
def knowledge(name, default=None): return configured("knowledge.registry",name,default)
def security_role(name, default=None): return configured("security.roles",name,default)
def security_capability(name, default=None): return configured("security.capabilities",name,default)
def security_approval(name, default=None): return configured("security.approvals",name,default)
def filesystem_policy(name, default=None): return configured("security.filesystem",name,default)
def subprocess_policy(name, default=None): return configured("security.subprocess",name,default)
def scheduler_job(name, default=None): return configured("scheduler.jobs",name,default)
def scheduler_worker(name, default=None): return configured("scheduler.workers",name,default)
def integration_event(name, default=None): return configured("integrations.events",name,default)
def webhook(name, default=None): return configured("integrations.webhooks",name,default)
def evaluation(name, default=None): return configured("agent.evaluation",name,default)
def regression(name, default=None): return configured("agent.regression",name,default)
def budget(name, default=None): return configured("agent.budget",name,default)
def cache_policy(name, default=None): return configured("agent.cache",name,default)
def skill(name, default=None): return configured("agent.skills",name,default)
def knowledge_graph(name, default=None): return configured("agent.knowledge_graph",name,default)
def research_agent(name, default=None): return configured("research.policy",name,default)
def event_policy(name, default=None): return configured("integrations.events",name,default)



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
