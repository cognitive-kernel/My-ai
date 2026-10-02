"""Version-aware knowledge and experience evolution helpers."""
from __future__ import annotations
import re, time
from dataclasses import dataclass, asdict
from typing import Any


@dataclass
class VersionKnowledge:
    subject: str
    version: str
    status: str = "valid"
    compatibility: str = ""
    valid_from: str | None = None
    valid_until: str | None = None
    replaced_by: str | None = None
    source: str = ""
    evidence: list[dict[str, Any]] | None = None

    def supports(self, target_version: str) -> bool:
        if self.compatibility:
            m=re.search(r">=\s*([0-9.]+)\s*,?\s*<\s*([0-9.]+)",self.compatibility)
            if m:
                def v(x): return tuple(int(p) for p in re.findall(r"\d+",x))
                return v(target_version)>=v(m.group(1)) and v(target_version)<v(m.group(2))
        return self.version == target_version or self.status == "valid"


class VersionKnowledgeStore:
    def __init__(self): self.items: list[VersionKnowledge]=[]
    def add(self,item): self.items.append(item); return item
    def candidates(self,subject,target_version):
        return [x for x in self.items if x.subject==subject and x.status not in {"removed","deprecated"} and x.supports(target_version)]
    def evolution(self,subject): return [asdict(x) for x in self.items if x.subject==subject]
    def mark(self,subject,version,status,replaced_by=None):
        for x in self.items:
            if x.subject==subject and x.version==version:
                x.status=status; x.replaced_by=replaced_by
        return self.evolution(subject)


@dataclass
class Experience:
    task: str
    outcome: str
    environment_version: str = ""
    model_version: str = ""
    provider_version: str = ""
    tool_version: str = ""
    skill_version: str = ""
    prompt_version: str = ""
    conditions: dict[str,Any] | None = None
    evidence: list[dict[str,Any]] | None = None
    lesson: str = ""
    compatibility: str = ""
    status: str = "valid"
    created_at: float = 0.0

    def __post_init__(self):
        if not self.created_at: self.created_at=time.time()


class ExperienceEvolution:
    def __init__(self): self.items:list[Experience]=[]
    def record(self,experience): self.items.append(experience); return experience
    def compatible(self,experience,current_versions:dict[str,str]) -> bool:
        checks={"environment_version":"environment","model_version":"model","provider_version":"provider",
                "tool_version":"tool","skill_version":"skill","prompt_version":"prompt"}
        for attr,key in checks.items():
            old=getattr(experience,attr,""); new=current_versions.get(key,"")
            if old and new and old!=new: return False
        return experience.status=="valid"
    def invalidate(self,index,reason): self.items[index].status="invalid:"+reason
    def current_first(self,current_versions):
        valid=[x for x in self.items if x.status=="valid"]
        return sorted(valid,key=lambda x:sum(bool(getattr(x,k,"")) and getattr(x,k)==current_versions.get(k) for k in
            ("environment_version","model_version","provider_version","tool_version","skill_version","prompt_version")),reverse=True)
    def compare(self,task): return [asdict(x) for x in self.items if x.task==task]
