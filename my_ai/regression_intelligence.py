"""Regression intelligence for candidate versus baseline evaluation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class RegressionDelta:
    metric: str
    baseline: float
    candidate: float
    delta: float
    improved: bool


class RegressionIntelligence:
    def __init__(self): self.baselines={}; self.candidates={}
    def save_baseline(self,name,metrics): self.baselines[name]=dict(metrics); return self.baselines[name]
    def compare(self,name,metrics):
        base=self.baselines.get(name,{})
        deltas=[]
        for key,val in metrics.items():
            if key not in base: continue
            b=float(base[key]); v=float(val); higher=key not in {"latency","cost","tokens","errors"}
            deltas.append(RegressionDelta(key,b,v,v-b,(v>b if higher else v<b)))
        return deltas
    def promote(self,name,metrics,gate:Callable[[list[RegressionDelta]],bool]):
        deltas=self.compare(name,metrics)
        return {"approved":bool(gate(deltas)),"deltas":[d.__dict__ for d in deltas]}
