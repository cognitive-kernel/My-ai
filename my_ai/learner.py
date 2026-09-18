from __future__ import annotations
import json
from .curriculum import next_topic
from .db import execute,fetch_all,search_knowledge
from .executor import run_python
from .llm import OllamaClient
from .memory import remember
from .web_learner import WebLearner
class LearningEngine:
    def __init__(self,llm=None): self.llm=llm or OllamaClient(); self.web=WebLearner()
    def study_url(self,url,topic="Python"):
        title,source=self.web.fetch(url)
        note=self.llm.chat("Extract accurate durable knowledge from this programming source. Return a structured study note with definitions, rules, examples, pitfalls and tests. Do not invent facts.\n\n"+source,system="You are a meticulous programming teacher.")
        remember(topic,title,note,url); return {"title":title,"source_url":url,"knowledge":note}
    def start(self,language="Python"):
        rows=fetch_all("SELECT topic FROM learning_sessions WHERE language=? AND status='completed'",(language,))
        topic=next_topic(language,{str(r["topic"]) for r in rows})
        if not topic:return {"status":"completed","message":f"{language} curriculum is complete."}
        sid=execute("INSERT INTO learning_sessions(language,topic,status,notes) VALUES(?,?,?,?)",(language,str(topic["topic"]),"started",json.dumps(topic,ensure_ascii=False)))
        return {"status":"started","session_id":sid,"topic":topic}
    def autonomous_step(self,language="Python"):
        s=self.start(language)
        if s["status"]=="completed":return s
        t=s["topic"]; k=search_knowledge(f"{language} {t['topic']}",6)
        lesson=self.llm.chat(f"Study {t['topic']} with goal {t['goal']}. Create a rigorous lesson, exercise and answer key.\nKNOWLEDGE:\n{json.dumps(k,ensure_ascii=False)}")
        remember(language,f"Study note: {t['topic']}",lesson)
        score=self.assess(t["topic"],lesson)
        execute("UPDATE learning_sessions SET status='completed',score=?,notes=? WHERE id=?",(score,lesson,s["session_id"]))
        return {"status":"completed","session_id":s["session_id"],"topic":t,"score":score}
    def assess(self,topic,lesson):
        try:return max(0,min(100,float(self.llm.chat("Score only 0-100 for factual coverage of this topic. Topic:"+topic+"\nNOTE:"+lesson).strip())))
        except ValueError:return 0
    def practice(self,task,language="Python"):
        return {"exercise":self.llm.chat(f"Create one {language} exercise. Return JSON keys description, starter_code, expected_behavior, hidden_tests. Task: {task}")}
    def validate_code(self,code):
        r=run_python(code); p=r.return_code==0 and not r.timed_out
        execute("INSERT INTO experiments(language,code,output,error,passed) VALUES(?,?,?,?,?)",("Python",code,r.output,r.error,int(p)))
        return {"passed":p,"output":r.output,"error":r.error,"return_code":r.return_code,"timed_out":r.timed_out}
    def status(self,language=None):
        return fetch_all("SELECT * FROM learning_sessions WHERE language=? ORDER BY id DESC",(language,)) if language else fetch_all("SELECT * FROM learning_sessions ORDER BY id DESC")
