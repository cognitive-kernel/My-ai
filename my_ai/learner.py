from __future__ import annotations
import json
from .curriculum import next_topic,canonical_language,source_urls
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
    def learn_next(self,language="Python"):
        language=canonical_language(language)
        s=self.start(language)
        if s["status"]=="completed": return s
        t=s["topic"]
        sources=source_urls(language)
        knowledge=[]
        for url in sources[:2]:
            try:
                title,source=self.web.fetch(url)
                note=self.llm.chat("Extract only accurate knowledge relevant to this topic from the source. Topic: "+t["topic"]+"\\n\\n"+source,system="You are a rigorous programming teacher. Cite concepts from the supplied source and never invent facts.")
                remember(language,title,note,url); knowledge.append({"title":title,"url":url})
            except Exception as exc:
                knowledge.append({"url":url,"error":str(exc)})
        lesson=self.llm.chat("Teach this topic using the supplied knowledge. Create a concise lesson, examples, exercises, tests, common mistakes and a mastery checklist. Topic: "+t["topic"]+" Goal: "+t["goal"]+"\\nKnowledge: "+json.dumps(search_knowledge(language+" "+t["topic"],8),ensure_ascii=False))
        remember(language,"Mastery lesson: "+t["topic"],lesson)
        score=self.assess(t["topic"],lesson)
        execute("UPDATE learning_sessions SET status='completed',score=?,notes=? WHERE id=?",(score,lesson,s["session_id"]))
        return {"status":"completed","session_id":s["session_id"],"language":language,"topic":t,"score":score,"sources":knowledge}
\n    def autonomous_step(self,language="Python"):
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
    def generate_program(self,request,language="Python"):
        prompt=(f"Write a complete, runnable {language} program for this user request:\n{request}\n"
                "Return ONLY source code, no markdown fences. Prefer standard library, clear structure, input validation and helpful comments.")
        code=self.llm.chat(prompt,system="You are a careful senior software engineer.").strip()
        if code.startswith("```"):
            lines=code.splitlines()
            lines=lines[1:] if lines else lines
            lines=lines[:-1] if lines and lines[-1].strip()=="```" else lines
            code="\n".join(lines).strip()
        result={"language":language,"request":request,"code":code}
        if language.lower()=="python": result["validation"]=self.validate_code(code)
        return result

    def generate_program(self,request,language="Python"):
        language=canonical_language(language)
        context=search_knowledge(language+" programming",12)
        prompt=("Write a complete runnable "+language+" program for the user request. Use the accumulated learning knowledge below. "
                "Return ONLY source code. Validate inputs, handle errors, use clear structure and comments.\\nREQUEST: "+request+
                "\\nKNOWLEDGE: "+json.dumps(context,ensure_ascii=False))
        code=self.llm.chat(prompt,system="You are a senior software engineer. Never claim execution unless a result is supplied.").strip()
        fence=chr(96)*3
        if code.startswith(fence):
            lines=code.splitlines()[1:]
            if lines and lines[-1].strip()==fence: lines=lines[:-1]
            code="\\n".join(lines).strip()
        result={"language":language,"request":request,"code":code}
        if language.lower()=="python": result["validation"]=self.validate_code(code)
        return result

    def validate_code(self,code):
        r=run_python(code); p=r.return_code==0 and not r.timed_out
        execute("INSERT INTO experiments(language,code,output,error,passed) VALUES(?,?,?,?,?)",("Python",code,r.output,r.error,int(p)))
        return {"passed":p,"output":r.output,"error":r.error,"return_code":r.return_code,"timed_out":r.timed_out}
    def status(self,language=None):
        rows=fetch_all("SELECT * FROM learning_sessions WHERE language=? ORDER BY id DESC",(language,)) if language else fetch_all("SELECT * FROM learning_sessions ORDER BY id DESC")
        from .curriculum import CURRICULA
        out=[]
        for lang,topics in CURRICULA.items():
            total=len(topics)
            completed=sum(1 for r in rows if r["language"]==lang and r["status"]=="completed")
            scores=[float(r["score"]) for r in rows if r["language"]==lang and r["status"]=="completed" and r["score"] is not None]
            out.append({"language":lang,"completed_topics":completed,"total_topics":total,"progress_percent":round(completed/total*100,1) if total else 0,"average_score":round(sum(scores)/len(scores),1) if scores else 0})
        if language: out=[x for x in out if x["language"].lower()==language.lower()]
        return {"languages":out,"sessions":rows,"available_languages":list(CURRICULA.keys())}
