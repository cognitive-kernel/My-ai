from __future__ import annotations
import json
from .curriculum import next_topic,canonical_language,source_urls,LANGUAGE_CURRICULA
from .advanced_curriculum import seed_for
from .db import execute,fetch_all,search_knowledge
from .executor import run_python
from .llm import create_llm
from .memory import remember
from .web_learner import WebLearner
from .security import SecurityEngine
from .dast import LocalDAST

class LearningEngine:
    def __init__(self,llm=None):
        self.llm=llm or create_llm(); self.web=WebLearner()
        self.security=SecurityEngine(self.llm); self.dast=LocalDAST()

    def _discover_prerequisites(self,language,topic):
        prompt=("You are a curriculum architect. Analyze the requested programming subject and identify prerequisite subjects that must be learned before or alongside it. "
                 '{"prerequisites":[{"name":"...","reason":"...","recommended_order":1}]}. '
                 "Do not duplicate the main topic. Only include concrete skills needed to build real projects. "
                 f"MAIN SUBJECT: {language}\nCURRENT TOPIC: {topic['topic']}\nGOAL: {topic['goal']}")
        try:
            data=json.loads(self.llm.chat(prompt,system="Return valid JSON only. Prefer official ecosystem prerequisites."))
            return data.get("prerequisites",[]) if isinstance(data,dict) else []
        except Exception: return []

    def _learn_sources_for_topic(self,language,topic,prerequisites):
        queries=[topic["topic"]]+[p.get("name","") for p in prerequisites[:3]]
        knowledge=[]
        seed=seed_for(language,topic["topic"])
        if seed:
            remember(language,"Model knowledge seed: "+topic["topic"],seed,"model://knowledge-seed")
            knowledge.append({"title":"Model knowledge seed","url":"model://knowledge-seed"})
        for url in source_urls(language)[:2]:
            try:
                title,source=self.web.fetch(url)
                note=self.llm.chat("Extract only accurate knowledge relevant to these study targets from the supplied source. "
                                    "Separate the targets and state prerequisites explicitly. Never invent facts.\n"
                                    f"LANGUAGE: {language}\nTARGETS: {json.dumps(queries,ensure_ascii=False)}\nSOURCE:\n{source}",
                                    system="You are a rigorous programming teacher.")
                remember(language,title,note,url); knowledge.append({"title":title,"url":url})
            except Exception as exc: knowledge.append({"url":url,"error":str(exc)})
        return knowledge

    def study_url(self,url,topic="Python"):
        title,source=self.web.fetch(url)
        note=self.llm.chat(
            "Study the supplied source and produce a concise, accurate learning note. "
            "Use only information supported by the source; identify uncertainty instead of inventing facts. "
            f"\nTOPIC: {topic}\nSOURCE TITLE: {title}\nSOURCE URL: {url}\nSOURCE:\n{source}",
            system="You are a rigorous programming teacher."
        )
        remember(topic,title,note,url)
        return {"title":title,"url":url,"topic":topic,"content":note}

    def start(self,language="Python"):
        language=canonical_language(language)
        active=fetch_all("SELECT * FROM learning_sessions WHERE language=? AND status='started' ORDER BY id DESC LIMIT 1",(language,))
        if active:
            row=active[0]
            try: topic=json.loads(row["notes"] or "{}")
            except Exception: topic={}
            if topic.get("topic"):
                return {"status":"started","session_id":row["id"],"topic":topic}
        rows=fetch_all("SELECT topic FROM learning_sessions WHERE language=? AND status='completed'",(language,))
        topic=next_topic(language,{str(r["topic"]) for r in rows})
        if not topic:return {"status":"completed","message":f"{language} curriculum is complete."}
        sid=execute("INSERT INTO learning_sessions(language,topic,status,notes,progress_percent,phase) VALUES(?,?,?,?,?,?)",(language,str(topic["topic"]),"started",json.dumps(topic,ensure_ascii=False),0.0,"starting"))
        return {"status":"started","session_id":sid,"topic":topic}

    def learn_next(self,language="Python",progress_callback=None):
        language=canonical_language(language); s=self.start(language)
        if s["status"]=="completed": return s
        t=s["topic"]
        self._set_progress(s["session_id"], 0.5, "prerequisites")
        if progress_callback: progress_callback("prerequisites",t["topic"])
        prerequisites=self._discover_prerequisites(language,t)
        self._set_progress(s["session_id"], 25.0, "sources")
        if progress_callback: progress_callback("sources",t["topic"])
        sources=self._learn_sources_for_topic(language,t,prerequisites)
        self._set_progress(s["session_id"], 50.0, "lesson")
        if progress_callback: progress_callback("lesson",t["topic"])
        seed=seed_for(language,t["topic"])
        lesson=self.llm.chat("Teach the topic as a complete, structured study unit. Include prerequisite lessons first, then the main topic, examples, exercises, tests, common mistakes, security considerations and a mastery checklist. "
                             "Use the model knowledge seed only as an initial layer; reconcile it with supplied official-source knowledge and explicitly correct conflicts. "
                             "Do not claim mastery unless supported by the supplied knowledge. Return clear sections.\n"
                             f"LANGUAGE: {language}\nTOPIC: {t['topic']}\nGOAL: {t['goal']}\n"
                             f"MODEL KNOWLEDGE SEED: {seed}\n"
                             f"DISCOVERED PREREQUISITES: {json.dumps(prerequisites,ensure_ascii=False)}\n"
                             f"LEARNED KNOWLEDGE: {json.dumps(search_knowledge(language+' '+t['topic'],12),ensure_ascii=False)}")
        remember(language,"Mastery lesson: "+t["topic"],lesson)
        self._set_progress(s["session_id"], 75.0, "assessment")
        if progress_callback: progress_callback("assessment",t["topic"])
        score=self.assess(t["topic"],lesson)
        execute("UPDATE learning_sessions SET status='completed',score=?,notes=?,progress_percent=100.0,phase='completed' WHERE id=?",(score,lesson,s["session_id"]))
        if progress_callback: progress_callback("completed",t["topic"])
        return {"status":"completed","session_id":s["session_id"],"language":language,"topic":t,"prerequisites":prerequisites,"score":score,"sources":sources,"seeded":bool(seed)}

    def autonomous_step(self,language="Python"): return self.learn_next(language)

    def assess(self,topic,lesson):
        import re
        try:
            raw=self.llm.chat("Return a numeric score from 0 to 100 for factual coverage. Topic:"+topic+"\nNOTE:"+lesson).strip()
            match=re.search(r"(?<!\d)(100(?:\.0+)?|(?:\d{1,2})(?:\.\d+)?)(?!\d)",raw)
            if not match:
                return None
            return max(0.0,min(100.0,float(match.group(1))))
        except (ValueError,TypeError):
            return None

    @staticmethod
    def _set_progress(session_id, progress, phase):
        execute("UPDATE learning_sessions SET progress_percent=?, phase=? WHERE id=?",(max(0.0,min(100.0,float(progress))),phase,session_id))

    def practice(self,task,language="Python"):
        return {"exercise":self.llm.chat(f"Create one {language} exercise. Return JSON keys description, starter_code, expected_behavior, hidden_tests. Task: {task}")}

    def generate_program(self,request,language="Python"):
        language=canonical_language(language); context=search_knowledge(language+" programming",20)
        code=self.llm.chat("Write a complete runnable "+language+" program for the user request. Use accumulated learning knowledge. "
                            "Apply secure coding practices, validate inputs, avoid unsafe defaults, include appropriate error handling and tests where practical. "
                            "Return ONLY source code.\nREQUEST: "+request+"\nKNOWLEDGE: "+json.dumps(context,ensure_ascii=False),
                            system="You are a senior secure software engineer. Never claim execution unless a result is supplied.").strip()
        fence=chr(96)*3
        if code.startswith(fence):
            lines=code.splitlines()[1:]
            if lines and lines[-1].strip()==fence: lines=lines[:-1]
            code="\n".join(lines).strip()
        pid=execute("INSERT INTO generated_projects(language,request,code) VALUES(?,?,?)",(language,request,code))
        result={"language":language,"request":request,"code":code,"project_id":pid}
        if language.lower()=="python": result["validation"]=self.validate_code(code)
        return result

    def security_scan_code(self,code,language="Python",fix=False): return self.security.scan_code(code,language,fix)
    def security_scan_path(self,project_path,fix=False): return self.security.scan_path(project_path,fix)
    def security_assessment_url(self,target_url,headers=None): return {"static":{"status":"not_applicable","findings":[],"summary":{"critical":0,"high":0,"medium":0,"low":0}},"dynamic":self.dast.scan_url(target_url,explicit=True,headers=headers),"code":None,"fixed":False,"target":target_url}
    def security_assessment_code(self,code,language="Python",fix=False):
        static=self.security.scan_code(code,language,fix); final_code=static.get("fixed_code",code) if fix else code; dynamic=self.dast.scan_code(final_code,language); result={"static":static,"dynamic":dynamic,"code":final_code,"fixed":bool(fix and static.get("fixed_code"))}
        if fix and final_code!=code: result["post_static"]=self.security.scan_code(final_code,language,False)
        return result
    def security_assessment_path(self,project_path,fix=False):
        static=self.security.scan_path(project_path,fix); dynamic=self.dast.scan_path(project_path); return {"static":static,"dynamic":dynamic,"fixed":bool(fix and static.get("fixed"))}
    def latest_generated_project(self):
        rows=fetch_all("SELECT * FROM generated_projects ORDER BY id DESC LIMIT 1"); return rows[0] if rows else None
    def security_scan_latest_generated(self,fix=False):
        project=self.latest_generated_project()
        if not project:return {"status":"no_project","message":"No generated project is available for security testing."}
        result=self.security_assessment_code(project["code"],project["language"],fix)
        if fix and result.get("code") and result["code"]!=project["code"]: execute("UPDATE generated_projects SET code=? WHERE id=?",(result["code"],project["id"]))
        result["project_id"]=project["id"]; result["request"]=project["request"]; return result
    def validate_code(self,code):
        r=run_python(code); p=r.return_code==0 and not r.timed_out; execute("INSERT INTO experiments(language,code,output,error,passed) VALUES(?,?,?,?,?)",("Python",code,r.output,r.error,int(p))); return {"passed":p,"output":r.output,"error":r.error,"return_code":r.return_code,"timed_out":r.timed_out}
    @staticmethod
    def _half_percent(value): return max(0.0,min(100.0,round(float(value)*2)/2))

    def status(self,language=None):
        rows=fetch_all("SELECT * FROM learning_sessions ORDER BY id DESC"); out=[]
        for lang,topics in LANGUAGE_CURRICULA.items():
            topic_names={str(x["topic"]) for x in topics}
            lang_rows=[r for r in rows if r["language"]==lang and str(r["topic"]) in topic_names]
            completed_topics={str(r["topic"]) for r in lang_rows if r["status"]=="completed"}
            completed=len(completed_topics); total=len(topics)
            active_progress=max([float(r["progress_percent"] or 0) for r in lang_rows if r["status"]!="completed" and r["progress_percent"] is not None] or [0.0])
            raw=((completed + active_progress/100.0) / total * 100.0) if total else 0.0
            scores=[float(r["score"]) for r in lang_rows if r["status"]=="completed" and r["score"] is not None]
            out.append({"language":lang,"completed_topics":completed,"total_topics":total,"progress_percent":self._half_percent(raw),"progress_step":"0.5%","average_score":round(sum(scores)/len(scores),1) if scores else 0})
        if language: out=[x for x in out if x["language"].lower()==canonical_language(language).lower()]
        return {"languages":out,"sessions":rows,"available_languages":list(LANGUAGE_CURRICULA.keys())}

