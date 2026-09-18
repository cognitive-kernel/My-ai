from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI,HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,HttpUrl
from .agent import Agent
from .command_policy import parse_command
from .config import settings
from .curriculum import canonical_language,LANGUAGE_CURRICULA
from .db import fetch_all,init_db
from .learner import LearningEngine
from .scheduler import StudyScheduler
from .ui import page

scheduler=StudyScheduler()
@asynccontextmanager
async def lifespan(_): init_db(); yield; scheduler.stop()
app=FastAPI(title="My-AI",version="0.2.0",description="Local-first personal learning and coding agent.",lifespan=lifespan)
agent=Agent(); learner=LearningEngine()
class ChatRequest(BaseModel): message:str
class URLRequest(BaseModel): url:HttpUrl; topic:str="Python"
class ProjectRequest(BaseModel): goal:str
class CodeRequest(BaseModel): code:str
class ProgramRequest(BaseModel): request:str; language:str="Python"
class LanguageRequest(BaseModel): language:str="Python"
class SecurityRequest(BaseModel): project_path:str|None=None; code:str|None=None; language:str="Python"; fix:bool=False
class SchedulerRequest(BaseModel): language:str="Python"; interval_seconds:int=3600
class LearnRequest(BaseModel): language:str="Python"; interval_seconds:int=3600

@app.get("/",response_class=HTMLResponse)
def home(): return page()
@app.get("/health")
def health(): return {"status":"ok","model":settings.ollama_model}

@app.post("/chat")
def chat(r:ChatRequest):
    try:
        msg=r.message.strip(); low=msg.lower()
        aliases={"sql server":"SQL Server","sqlserver":"SQL Server","mssql":"SQL Server","mysql":"MySQL","sqlite":"SQLite","sql lite":"SQLite","android":"Android","اندروید":"Android","ios":"iOS","آی او اس":"iOS","python":"Python","پایتون":"Python","php":"PHP","c":"C","javascript":"JavaScript","js":"JavaScript","pentest":"Pentest","pen test":"Pentest","penetration testing":"Pentest","penetration test":"Pentest","پنتست":"Pentest","پن تست":"Pentest","تست نفوذ":"Pentest","امنیت":"Pentest"}
        requested=next((name for key,name in sorted(aliases.items(),key=lambda x:len(x[0]),reverse=True) if key in low),None)
        learn_intent=("یاد بگیر" in low or "یادگیری" in low or "learn" in low or "go learn" in low or "start learning" in low)
        policy=parse_command(msg); security_words=policy.security; fix_requested=policy.security_action=="fix"
        code_words=("برنامه بنویس","کد بنویس","برام برنامه","write a program","write code","program","build an app","create an app")
        code_intent=any(x in low for x in code_words)
        if security_words:
            if code_intent:
                language=requested or "Python"; generated=learner.generate_program(msg,language)
                result=learner.security_assessment_code(generated["code"],language,fix_requested)
                result["generated_project"]=generated; result["mode"]="pentest_and_fix" if fix_requested else "pentest_report"
                return {"type":"security","answer":"Security test completed with static + local dynamic checks." if not fix_requested else "Security test, remediation and retest completed.","data":result}
            path=None
            for prefix in ("مسیر:","path:","project:","پروژه:"):
                if prefix in msg: path=msg.split(prefix,1)[1].strip().strip('"\''); break
            if path:
                result=learner.security_assessment_path(path,fix_requested); result["mode"]="pentest_and_fix" if fix_requested else "pentest_report"
                return {"type":"security","answer":"Security test completed with static + local dynamic checks." if not fix_requested else "Security test, remediation and retest completed.","data":result}
            result=learner.security_scan_latest_generated(fix_requested)
            if result.get("status")=="no_project":
                return {"type":"security","answer":"برای پن‌تست پروژه خودت، مسیر پوشه پروژه را بده؛ مثال: «پن تست مسیر: C:\\projects\\login». پروژه تولیدشده آخر هم خودکار بررسی می‌شود.","data":result}
            result["mode"]="pentest_and_fix" if fix_requested else "pentest_report"
            return {"type":"security","answer":"Security test completed with static + local dynamic checks." if not fix_requested else "Security test, remediation and retest completed.","data":result}
        if learn_intent:
            language=requested or "Python"; return {"type":"learning","answer":f"Learning step completed for {canonical_language(language)}.","data":learner.learn_next(language)}
        if code_intent:
            language=requested or "Python"; return {"type":"code","answer":"Generated program:","data":learner.generate_program(msg,language)}
        return {"type":"chat","answer":agent.chat(msg)}
    except Exception as e: raise HTTPException(502,str(e))

@app.post("/learn/url")
def learn_url(r:URLRequest):
    try:return learner.study_url(str(r.url),r.topic)
    except Exception as e: raise HTTPException(400,str(e))
@app.post("/learning/start")
def learning_start(r:LanguageRequest): return learner.start(r.language)
@app.post("/learning/step")
def learning_step(r:LanguageRequest):
    try:return learner.learn_next(r.language)
    except Exception as e: raise HTTPException(502,str(e))
@app.get("/learning/status")
def learning_status(language:str|None=None): return learner.status(language)
@app.post("/learning/practice")
def practice(r:ChatRequest):
    try:return learner.practice(r.message)
    except Exception as e: raise HTTPException(502,str(e))
@app.post("/code/run")
def code_run(r:CodeRequest): return learner.validate_code(r.code)
@app.post("/code/generate")
def code_generate(r:ProgramRequest):
    try:return learner.generate_program(r.request,r.language)
    except Exception as e: raise HTTPException(502,str(e))
@app.post("/security/scan")
def security_scan(r:SecurityRequest):
    try:
        if r.project_path: return learner.security_assessment_path(r.project_path,r.fix)
        if r.code: return learner.security_assessment_code(r.code,r.language,r.fix)
        return learner.security_scan_latest_generated(r.fix)
    except Exception as e: raise HTTPException(400,str(e))
@app.get("/security/history")
def security_history(limit:int=20): return learner.security.history(limit)
@app.get("/languages")
def languages(): return {"languages":list(LANGUAGE_CURRICULA.keys())}
@app.post("/projects/plan")
def project_plan(r:ProjectRequest):
    try:return {"tasks":agent.plan_project(r.goal)}
    except Exception as e: raise HTTPException(502,str(e))
@app.get("/memory/knowledge")
def knowledge(): return fetch_all("SELECT * FROM knowledge ORDER BY id DESC")
@app.get("/memory/search")
def memory_search(q:str,limit:int=8):
    from .memory import recall
    return recall(q,limit)
@app.get("/projects/tasks")
def project_tasks(): return fetch_all("SELECT * FROM project_tasks ORDER BY id")
@app.post("/scheduler/start")
def scheduler_start(r:SchedulerRequest):
    if not 60<=r.interval_seconds<=86400: raise HTTPException(400,"interval_seconds must be 60..86400")
    scheduler.interval_seconds=r.interval_seconds; scheduler.start(r.language)
    return {"status":"started","language":r.language,"interval_seconds":r.interval_seconds}
@app.get("/scheduler/status")
def scheduler_status(): return {"running":scheduler.running(),"language":scheduler.language,"last_result":scheduler.last_result}
@app.post("/learning/learn")
def learning_learn(r:LearnRequest):
    if not 60<=r.interval_seconds<=86400: raise HTTPException(400,"interval_seconds must be 60..86400")
    scheduler.interval_seconds=r.interval_seconds; scheduler.start(r.language)
    return {"status":"started","language":r.language,"interval_seconds":r.interval_seconds}
@app.post("/scheduler/stop")
def scheduler_stop(): scheduler.stop(); return {"status":"stopped"}
