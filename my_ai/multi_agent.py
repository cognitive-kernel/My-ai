"""Adaptive multi-agent coordination without training a custom model."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AgentSpec:
    name: str
    role: str
    capabilities: set[str] = field(default_factory=set)
    priority: int = 100


class MultiAgentCoordinator:
    def __init__(self, agents: list[AgentSpec] | None=None):
        self.agents={a.name:a for a in (agents or [])}
    def register(self,agent): self.agents[agent.name]=agent
    def select(self, task: str, required: set[str] | None=None):
        required=required or set()
        return sorted([a for a in self.agents.values() if required<=a.capabilities], key=lambda a:a.priority)
    def run_parallel(self, task: str, workers: dict[str,Callable], required=None):
        selected=self.select(task,required)
        outputs={}
        for a in selected:
            fn=workers.get(a.name)
            if fn: outputs[a.name]=fn(task)
        return outputs
    def synthesize(self, outputs: dict[str,Any], verifier: Callable[[Any],bool] | None=None):
        candidates=list(outputs.values())
        if verifier: candidates=[x for x in candidates if verifier(x)]
        return candidates[0] if candidates else None
