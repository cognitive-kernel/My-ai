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
        if self.version == target_version: return self.status == "valid"
        return self.status in {"compatible","valid-compatible"} and bool(self.compatibility)


class VersionKnowledgeStore:
    def __init__(self): self.items: list[VersionKnowledge]=[]
    def add(self,item): self.items.append(item); return item
    def candidates(self,subject,target_version):
        items=[x for x in self.items if x.subject==subject and x.status not in {"removed","deprecated"} and x.supports(target_version)]
        return sorted(items,key=lambda x:(x.version==target_version, x.status=="valid"),reverse=True)
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


# Persistent stores are additive so existing in-memory callers remain compatible.
from .db import connect

_PERSISTENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS version_knowledge (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 subject TEXT NOT NULL,
 version TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'valid',
 compatibility TEXT NOT NULL DEFAULT '',
 valid_from TEXT,
 valid_until TEXT,
 replaced_by TEXT,
 source TEXT NOT NULL DEFAULT '',
 evidence_json TEXT NOT NULL DEFAULT '[]',
 created_at REAL NOT NULL,
 updated_at REAL NOT NULL,
 UNIQUE(subject,version)
);
CREATE TABLE IF NOT EXISTS experience_evolution (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 task TEXT NOT NULL,
 outcome TEXT NOT NULL,
 environment_version TEXT NOT NULL DEFAULT '',
 model_version TEXT NOT NULL DEFAULT '',
 provider_version TEXT NOT NULL DEFAULT '',
 tool_version TEXT NOT NULL DEFAULT '',
 skill_version TEXT NOT NULL DEFAULT '',
 prompt_version TEXT NOT NULL DEFAULT '',
 conditions_json TEXT NOT NULL DEFAULT '{}',
 evidence_json TEXT NOT NULL DEFAULT '[]',
 lesson TEXT NOT NULL DEFAULT '',
 compatibility TEXT NOT NULL DEFAULT '',
 status TEXT NOT NULL DEFAULT 'valid',
 created_at REAL NOT NULL,
 invalidation_reason TEXT NOT NULL DEFAULT ''
);
"""

def ensure_evolution_schema():
    with connect() as conn:
        conn.executescript(_PERSISTENT_SCHEMA)
        conn.commit()


class PersistentVersionKnowledgeStore(VersionKnowledgeStore):
    def __init__(self):
        super().__init__()
        ensure_evolution_schema()
        self._load_persistent()

    def _load_persistent(self):
        import json
        with connect() as conn:
            rows=conn.execute("SELECT subject,version,status,compatibility,valid_from,valid_until,replaced_by,source,evidence_json FROM version_knowledge ORDER BY created_at,id").fetchall()
        self.items=[
            VersionKnowledge(subject=str(r["subject"]),version=str(r["version"]),status=str(r["status"]),
                            compatibility=str(r["compatibility"] or ""),valid_from=r["valid_from"],valid_until=r["valid_until"],
                            replaced_by=r["replaced_by"],source=str(r["source"] or ""),evidence=json.loads(r["evidence_json"] or "[]"))
            for r in rows
        ]

    def add(self,item):
        super().add(item)
        import json
        now=time.time()
        with connect() as conn:
            conn.execute("""INSERT INTO version_knowledge
                (subject,version,status,compatibility,valid_from,valid_until,replaced_by,source,evidence_json,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(subject,version) DO UPDATE SET status=excluded.status,compatibility=excluded.compatibility,
                valid_from=excluded.valid_from,valid_until=excluded.valid_until,replaced_by=excluded.replaced_by,
                source=excluded.source,evidence_json=excluded.evidence_json,updated_at=excluded.updated_at""",
                (item.subject,item.version,item.status,item.compatibility,item.valid_from,item.valid_until,item.replaced_by,
                 item.source,json.dumps(item.evidence or [],ensure_ascii=False),now,now))
            conn.commit()
        return item

    def mark(self,subject,version,status,replaced_by=None):
        result=super().mark(subject,version,status,replaced_by)
        with connect() as conn:
            conn.execute("UPDATE version_knowledge SET status=?,replaced_by=?,updated_at=? WHERE subject=? AND version=?",
                         (status,replaced_by,time.time(),subject,version))
            conn.commit()
        return result

    def compare(self,subject,first_version,second_version):
        first=next((asdict(x) for x in self.items if x.subject==subject and x.version==first_version),None)
        second=next((asdict(x) for x in self.items if x.subject==subject and x.version==second_version),None)
        return {"subject":subject,"first":first,"second":second,"same":first==second}


class PersistentExperienceEvolution(ExperienceEvolution):
    def __init__(self):
        super().__init__()
        ensure_evolution_schema()
        self._load_persistent()

    def _load_persistent(self):
        import json
        with connect() as conn:
            rows=conn.execute("SELECT * FROM experience_evolution ORDER BY created_at,id").fetchall()
        self.items=[Experience(task=str(r["task"]),outcome=str(r["outcome"]),
            environment_version=str(r["environment_version"] or ""),model_version=str(r["model_version"] or ""),
            provider_version=str(r["provider_version"] or ""),tool_version=str(r["tool_version"] or ""),
            skill_version=str(r["skill_version"] or ""),prompt_version=str(r["prompt_version"] or ""),
            conditions=json.loads(r["conditions_json"] or "{}"),evidence=json.loads(r["evidence_json"] or "[]"),
            lesson=str(r["lesson"] or ""),compatibility=str(r["compatibility"] or ""),status=str(r["status"]),
            created_at=float(r["created_at"])) for r in rows]

    def record(self,experience):
        super().record(experience)
        import json
        ensure_evolution_schema()
        with connect() as conn:
            conn.execute("""INSERT INTO experience_evolution
                (task,outcome,environment_version,model_version,provider_version,tool_version,skill_version,prompt_version,
                 conditions_json,evidence_json,lesson,compatibility,status,created_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (experience.task,experience.outcome,experience.environment_version,experience.model_version,
                 experience.provider_version,experience.tool_version,experience.skill_version,experience.prompt_version,
                 json.dumps(experience.conditions or {},ensure_ascii=False),json.dumps(experience.evidence or [],ensure_ascii=False),
                 experience.lesson,experience.compatibility,experience.status,experience.created_at))
            conn.commit()
        return experience

    def invalidate(self,index,reason):
        super().invalidate(index,reason)
        with connect() as conn:
            row=conn.execute("SELECT id FROM experience_evolution ORDER BY created_at,id LIMIT 1 OFFSET ?",(index,)).fetchone()
            if row:
                conn.execute("UPDATE experience_evolution SET status=?,invalidation_reason=? WHERE id=?",
                             ("invalid:"+reason,reason,int(row["id"])))
                conn.commit()

    def invalidate_incompatible(self,current_versions,reason="version-mismatch"):
        changed=0
        for index,item in enumerate(list(self.items)):
            if item.status=="valid" and not self.compatible(item,current_versions):
                self.invalidate(index,reason); changed+=1
        return changed
