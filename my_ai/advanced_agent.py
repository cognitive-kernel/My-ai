"""Advanced agent intelligence primitives.

These components are deterministic orchestration infrastructure. They do not train
or replace an LLM; they make models, tools, memory and verification composable,
version-aware and configurable.
"""
from __future__ import annotations
import hashlib, time, uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


@dataclass
class Skill:
    name: str
    version: str = "1"
    description: str = ""
    prerequisites: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)
    success_rate: float = 0.0
    verified: bool = False
    enabled: bool = False


class SkillRegistry:
    def __init__(self): self._items: dict[str, Skill] = {}
    def propose(self, skill: Skill) -> Skill: skill.enabled=False; skill.verified=False; self._items[skill.name]=skill; return skill
    def verify(self, name: str, verifier: Callable[[Skill], bool]) -> Skill:
        s=self._items[name]; s.verified=bool(verifier(s)); s.enabled=s.verified; return s
    def rollback(self, name: str) -> None:
        if name in self._items: self._items[name].enabled=False
    def select(self, task: str, available_tools: Iterable[str]=()) -> list[Skill]:
        tools=set(available_tools)
        return sorted((s for s in self._items.values() if s.enabled and set(s.tools)<=tools),
                      key=lambda x:x.success_rate, reverse=True)


@dataclass(frozen=True)
class GraphEntity:
    id: str
    kind: str
    properties: dict[str, Any]


@dataclass(frozen=True)
class GraphRelation:
    source: str
    relation: str
    target: str
    valid_from: str | None = None
    valid_until: str | None = None
    version: str | None = None


class KnowledgeGraph:
    def __init__(self):
        self.entities: dict[str, GraphEntity] = {}
        self.relations: list[GraphRelation] = []
    def add_entity(self, kind: str, entity_id: str, **properties) -> GraphEntity:
        e=GraphEntity(entity_id,kind,properties); self.entities[entity_id]=e; return e
    def relate(self, source: str, relation: str, target: str, **meta) -> GraphRelation:
        r=GraphRelation(source,relation,target,meta.get("valid_from"),meta.get("valid_until"),meta.get("version")); self.relations.append(r); return r
    def neighbors(self, entity_id: str, relation: str | None=None) -> list[GraphEntity]:
        ids=[r.target for r in self.relations if r.source==entity_id and (relation is None or r.relation==relation)]
        return [self.entities[x] for x in ids if x in self.entities]


class HybridRetriever:
    def __init__(self, vector=None, keyword=None, graph: KnowledgeGraph | None=None):
        self.vector, self.keyword, self.graph = vector, keyword, graph
    def retrieve(self, query: str, *, metadata: dict[str, Any] | None=None, top_k: int=10, reranker=None):
        candidates=[]
        if self.keyword: candidates.extend(self.keyword(query, top_k*2, metadata or {}))
        if self.vector: candidates.extend(self.vector(query, top_k*2, metadata or {}))
        seen=set(); merged=[]
        for item in candidates:
            key=str(item.get("id") or hashlib.sha256(str(item).encode()).hexdigest())
            if key not in seen: seen.add(key); merged.append(item)
        if reranker: merged=reranker(query, merged)
        return merged[:top_k]


@dataclass(frozen=True)
class ContextPlan:
    items: list[dict[str, Any]]
    token_budget: int
    estimated_tokens: int


class ContextPlanner:
    def __init__(self, estimator: Callable[[str], int] | None=None):
        self.estimator=estimator or (lambda x:max(1,len(x)//4))
    def plan(self, items: list[dict[str, Any]], budget: int) -> ContextPlan:
        ranked=sorted(items,key=lambda x:float(x.get("priority",0)),reverse=True)
        selected=[]; used=0
        for item in ranked:
            n=self.estimator(str(item.get("content","")))
            if used+n>budget: continue
            selected.append(item); used+=n
        return ContextPlan(selected,budget,used)


@dataclass(frozen=True)
class Confidence:
    score: float
    reasons: tuple[str,...]
    action: str


class ConfidenceEngine:
    def score(self, *, source_quality: float=0, agreement: float=0, freshness: float=0,
              verification: float=0, historical_success: float=0) -> Confidence:
        vals=[max(0,min(1,float(x))) for x in (source_quality,agreement,freshness,verification,historical_success)]
        score=sum(vals)/len(vals)
        action="answer" if score>=.8 else ("verify" if score>=.55 else "research")
        return Confidence(round(score,4),("source","agreement","freshness","verification","history"),action)


class EvaluationLab:
    def __init__(self): self.suites: dict[str,list[dict[str,Any]]]={}; self.runs=[]
    def register(self,name,tasks): self.suites[name]=list(tasks)
    def run(self,name,runner:Callable[[dict[str,Any]],dict[str,Any]]) -> dict[str,Any]:
        results=[]
        for task in self.suites.get(name,[]): results.append(runner(task))
        summary={"suite":name,"count":len(results),"results":results,"timestamp":time.time()}
        self.runs.append(summary); return summary


class ResearchPipeline:
    def __init__(self, search, fetch, verifier=None, freshness=None, ranker=None):
        self.search,self.fetch,self.verifier=search,fetch,verifier
        self.freshness,self.ranker=freshness,ranker

    def run(self, question: str, manual_sources: list[str] | None=None, limit:int=8, *,
            allowed_domains: Iterable[str] | None=None, require_fresh: bool=False) -> dict[str,Any]:
        urls=list(dict.fromkeys((manual_sources or [])+list(self.search(question,limit))))
        domains={str(x).lower().lstrip(".") for x in (allowed_domains or [])}
        if domains:
            urls=[u for u in urls if any(str(u).lower().split("/")[2].endswith(d) for d in domains if "://" in str(u))]
        evidence=[]
        for url in urls:
            try:
                item=self.fetch(url)
                if isinstance(item, tuple) and len(item)>=2:
                    title, content=item[0], item[1]
                    record={"url":url,"title":str(title),"content":str(content)}
                elif isinstance(item,dict):
                    record=dict(item); record.setdefault("url",url)
                else:
                    record={"url":url,"content":str(item)}
                record["freshness"]=self.freshness(record) if self.freshness else None
                if require_fresh and self.freshness and not bool(record["freshness"]):
                    continue
                if self.verifier and not self.verifier(record):
                    continue
                evidence.append(record)
            except Exception as exc:
                evidence.append({"url":url,"error":str(exc),"verified":False})
        if self.ranker:
            evidence=list(self.ranker(question,evidence))
        # Lightweight contradiction detection: expose competing normalized claims to the caller
        # instead of silently selecting one source.
        claims=[str(x.get("claim") or x.get("summary") or "").strip() for x in evidence if str(x.get("claim") or x.get("summary") or "").strip()]
        contradictions=[]
        for i,left in enumerate(claims):
            for right in claims[i+1:]:
                if left.casefold()!=right.casefold() and any(token in right.casefold() for token in ("not ","false","deprecated","obsolete")):
                    contradictions.append({"left":left,"right":right})
        return {"question":question,"sources":[x.get("url") for x in evidence],"evidence":evidence,
                "contradictions":contradictions,"provenance":[{"url":x.get("url"),"title":x.get("title","")} for x in evidence],
                "generated_at":time.time()}


class SecureEnvironment:
    def __init__(self, policy): self.policy=policy
    def execute(self, operation: str, fn: Callable[[],Any]):
        decision=self.policy(operation)
        if decision not in ("allow","sandbox"): raise PermissionError("operation denied by policy")
        return fn()


class TaskGraph:
    def __init__(self): self.nodes={}
    def add(self,node_id,fn,deps=()): self.nodes[node_id]={"fn":fn,"deps":set(deps)}
    def ready(self,completed): return [n for n,v in self.nodes.items() if n not in completed and v["deps"]<=set(completed)]
    def run(self, executor):
        done=set(); results={}
        while len(done)<len(self.nodes):
            ready=self.ready(done)
            if not ready: raise RuntimeError("task dependency cycle")
            batch=executor([(n,self.nodes[n]["fn"]) for n in ready])
            results.update(batch); done.update(ready)
        return results


class SmartCache:
    def __init__(self, backend): self.backend=backend
    def key(self, namespace, value, version=""): return hashlib.sha256(f"{namespace}|{version}|{value}".encode()).hexdigest()
    def get(self, namespace, value, version=""): return self.backend.get(self.key(namespace,value,version))
    def put(self, namespace, value, result, version="", ttl=None): return self.backend.put(self.key(namespace,value,version),result,ttl=ttl)
    def invalidate(self, namespace, value, version=""):
        key=self.key(namespace,value,version)
        deleter=getattr(self.backend,"delete",None)
        if callable(deleter): return bool(deleter(key))
        return False


@dataclass
class ExecutionBudget:
    steps:int=20
    tokens:int=16000
    seconds:float=300
    tool_calls:int=20
    cost:float=1.0
    def allow(self, *, steps=0,tokens=0,seconds=0,tool_calls=0,cost=0):
        return self.steps>=steps and self.tokens>=tokens and self.seconds>=seconds and self.tool_calls>=tool_calls and self.cost>=cost
    def consume(self, *, steps=0,tokens=0,seconds=0,tool_calls=0,cost=0):
        self.steps-=steps; self.tokens-=tokens; self.seconds-=seconds; self.tool_calls-=tool_calls; self.cost-=cost


class EventWorkflow:
    def __init__(self, *, retry_limit: int = 3):
        self.handlers: dict[str,list[Callable]]={}
        self.retry_limit=max(0,int(retry_limit))
        self.dead_letters:list[dict[str,Any]]=[]
        self._seen:set[str]=set()
    def on(self,event,handler): self.handlers.setdefault(event,[]).append(handler)
    def emit(self,event,payload,*,event_id=None):
        event_id=str(event_id or uuid.uuid4())
        if event_id in self._seen: return []
        self._seen.add(event_id)
        outputs=[]
        for handler in self.handlers.get(event,()):
            last=None
            for attempt in range(self.retry_limit+1):
                try:
                    last=handler(payload); break
                except Exception as exc:
                    last=exc
                    if attempt>=self.retry_limit:
                        self.dead_letters.append({"event_id":event_id,"event":event,"payload":payload,"error":str(exc)})
            outputs.append(last)
        return outputs


class MetaAgent:
    def propose(self, metrics:dict[str,Any]) -> list[dict[str,Any]]:
        proposals=[]
        if metrics.get("latency_ms",0)>metrics.get("latency_budget_ms",float("inf")): proposals.append({"type":"routing","reason":"latency"})
        if metrics.get("tool_failures",0)>0: proposals.append({"type":"tool_policy","reason":"tool_failures"})
        if metrics.get("retrieval_recall",1)<metrics.get("target_recall",0): proposals.append({"type":"retrieval","reason":"recall"})
        return proposals

    def evaluate_candidate(self, candidate: dict[str, Any], *, sandbox: Callable[[dict[str,Any]], Any],
                           verify: Callable[[Any], bool], approve: Callable[[Any], bool] | None = None) -> dict[str, Any]:
        """Candidate -> sandbox -> verify -> optional approval; never mutates production directly."""
        result = sandbox(dict(candidate))
        verified = bool(verify(result))
        approved = bool(approve(result)) if verified and approve else verified
        return {"candidate": candidate, "sandbox_result": result, "verified": verified, "approved": approved}

class AgentOS:
    """Shared lifecycle registry for task/session/model/tool/skill/event/evaluation."""
    def __init__(self):
        self.sessions={}; self.tasks={}; self.models={}; self.tools={}; self.skills=SkillRegistry()
        self.events=EventWorkflow(); self.evaluations=EvaluationLab()
    def create_session(self, metadata=None):
        sid=str(uuid.uuid4()); self.sessions[sid]={"id":sid,"metadata":metadata or {},"created_at":time.time(),"status":"active"}; return self.sessions[sid]
    def create_task(self, session_id, kind, payload):
        tid=str(uuid.uuid4()); self.tasks[tid]={"id":tid,"session_id":session_id,"kind":kind,"payload":payload,"status":"queued"}; return self.tasks[tid]
    def transition(self, task_id, status): self.tasks[task_id]["status"]=status; return self.tasks[task_id]

@dataclass(frozen=True)
class ReasoningStep:
    phase: str
    value: Any
    verified: bool = False

class ReasoningCycle:
    """Adaptive Understand→Plan→Execute→Observe→Critique→Re-plan→Verify cycle."""
    def __init__(self, *, verifier=None, max_steps: int = 8, early_exit: bool = True):
        self.verifier = verifier
        self.max_steps = max(1, int(max_steps))
        self.early_exit = bool(early_exit)

    def run(self, task: Any, *, understand, plan, execute, observe=lambda x: x,
             critique=lambda x: None, replan=None) -> dict[str, Any]:
        steps: list[ReasoningStep] = [ReasoningStep("understand", understand(task))]
        current_plan = plan(steps[-1].value)
        steps.append(ReasoningStep("plan", current_plan))
        result = None
        for _ in range(self.max_steps):
            result = execute(current_plan)
            steps.append(ReasoningStep("execute", result))
            observed = observe(result)
            steps.append(ReasoningStep("observe", observed))
            criticism = critique(observed)
            steps.append(ReasoningStep("critique", criticism))
            verified = bool(self.verifier(observed)) if self.verifier else False
            steps.append(ReasoningStep("verify", observed, verified))
            if verified and self.early_exit:
                break
            if replan is None:
                break
            current_plan = replan(current_plan, criticism, observed)
            steps.append(ReasoningStep("re-plan", current_plan))
        return {"task": task, "result": result, "verified": bool(steps[-1].verified), "steps": [s.__dict__ for s in steps]}

class VerificationPipeline:
    """Task-aware independent verification with escalation hooks."""
    def __init__(self, verifiers: dict[str, Callable[[Any], bool]] | None = None, escalator=None):
        self.verifiers = verifiers or {}
        self.escalator = escalator

    def verify(self, task_type: str, value: Any, *, evidence=None) -> dict[str, Any]:
        verifier = self.verifiers.get(task_type) or self.verifiers.get("default")
        passed = bool(verifier(value)) if verifier else bool(evidence)
        escalated = False
        if not passed and self.escalator:
            escalated = True
            passed = bool(self.escalator(task_type, value, evidence))
        return {"task_type": task_type, "passed": passed, "escalated": escalated}

class AdaptiveEnsemble:
    """Use multiple agents only when complexity/risk justifies the extra work."""
    def __init__(self, coordinator, complexity_threshold: float = 0.7):
        self.coordinator = coordinator
        self.complexity_threshold = float(complexity_threshold)

    def should_escalate(self, *, complexity: float, risk: float = 0.0, importance: float = 0.0, budget: float = 1.0) -> bool:
        score = max(float(complexity), float(risk), float(importance))
        return score >= self.complexity_threshold and float(budget) > 0

    def run(self, task: Any, *, complexity: float, risk: float = 0.0, importance: float = 0.0,
            budget: float = 1.0, workers=None, required=None, verifier=None) -> dict[str, Any]:
        if not self.should_escalate(complexity=complexity, risk=risk, importance=importance, budget=budget):
            return {"mode": "single", "result": None, "outputs": {}}
        outputs = self.coordinator.run_parallel(task, workers or {}, required)
        return {"mode": "multi-agent", "result": self.coordinator.synthesize(outputs, verifier), "outputs": outputs}

