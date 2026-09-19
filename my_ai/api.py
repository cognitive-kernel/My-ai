from __future__ import annotations
from contextlib import asynccontextmanager
import re
from fastapi import FastAPI,HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,HttpUrl,Field
from .agent import Agent
from .command_policy import parse_command
from .config import settings
from .curriculum import canonical_language,LANGUAGE_CURRICULA
from .db import fetch_all,init_db,execute
from .learner import LearningEngine
from .scheduler import StudyScheduler
from .ui import page
from .help import page as help_page, ask_help
from .git_connector import GitHubConnector

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
class SecurityRequest(BaseModel): project_path:str|None=None; target_url:str|None=None; code:str|None=None; language:str="Python"; fix:bool=False; headers:dict[str,str]=Field(default_factory=dict)
class GitRequest(BaseModel): repository:str; path:str|None=None; ref:str|None=None; branch:str|None=None; content:str|None=None; message:str|None=None; allow_write:bool=False
class SchedulerRequest(BaseModel): language:str="Python"; interval_seconds:int=3600
class LearnRequest(BaseModel): language:str="Python"; interval_seconds:int=3600

@app.get("/",response_class=HTMLResponse)
def home():
    return HTMLResponse(
        page(),
        headers={
            "Cache-Control":"no-store, no-cache, must-revalidate, max-age=0",
            "Pragma":"no-cache",
            "Expires":"0",
        },
    )
@app.get("/help",response_class=HTMLResponse)
def help(): return help_page()
@app.get("/chat/history")
def chat_history(limit:int=100):
    limit=max(1,min(limit,500))
    rows=fetch_all("SELECT role,content,created_at FROM conversations ORDER BY id DESC LIMIT ?",(limit,))
    rows.reverse()
    return {"messages":rows}

@app.get("/help/updates")
def help_updates(status:str="pending"): return fetch_all("SELECT * FROM help_updates WHERE status=? ORDER BY id DESC",(status,))
@app.post("/help/ask")
def help_ask(r:ChatRequest):
    try:
        low=r.message.lower(); component="git" if any(x in low for x in ("git","github","گیت","گیت‌هاب")) else ("security" if any(x in low for x in ("امنیت","پن‌تست","pentest")) else ("docker" if "docker" in low else ("python" if "python" in low or "پایتون" in low else "general")))
        return ask_help(r.message,component,agent.llm,learner.web)
    except Exception as e: raise HTTPException(502,str(e))
@app.post("/help/approve/{update_id}")
def help_approve(update_id:int):
    rows=fetch_all("SELECT * FROM help_updates WHERE id=? AND status='pending'",(update_id,))
    if not rows: raise HTTPException(404,"Pending help update not found.")
    proposal=rows[0].get("proposed_update") or ""
    if proposal.strip()=="NO_CHANGE":
        execute("UPDATE help_updates SET status='rejected' WHERE id=?",(update_id,)); return {"status":"rejected","update_id":update_id,"message":"No documentation change was proposed."}
    execute("UPDATE help_updates SET status='approved' WHERE id=?",(update_id,))
    return {"status":"approved","update_id":update_id,"message":"The approved help update is now visible in /help."}
@app.post("/help/reject/{update_id}")
def help_reject(update_id:int):
    rows=fetch_all("SELECT * FROM help_updates WHERE id=? AND status='pending'",(update_id,))
    if not rows: raise HTTPException(404,"Pending help update not found.")
    execute("UPDATE help_updates SET status='rejected' WHERE id=?",(update_id,)); return {"status":"rejected","update_id":update_id}
@app.get("/health")
def health(): return {"status":"ok","model":settings.ollama_model,"executor_mode":settings.exec_mode}

@app.post("/chat")
def chat(r:ChatRequest):
    try:
        msg=r.message.strip(); low=msg.lower()
        aliases={"sql server":"SQL Server","sqlserver":"SQL Server","mssql":"SQL Server","mysql":"MySQL","sqlite":"SQLite","sql lite":"SQLite","android":"Android","اندروید":"Android","ios":"iOS","آی او اس":"iOS","python":"Python","پایتون":"Python","php":"PHP","c":"C","javascript":"JavaScript","js":"JavaScript","pentest":"Pentest","pen test":"Pentest","penetration testing":"Pentest","penetration test":"Pentest","پنتست":"Pentest","پن تست":"Pentest","تست نفوذ":"Pentest","امنیت":"Pentest"}; requested=next((name for key,name in sorted(aliases.items(),key=lambda x:len(x[0]),reverse=True) if key in low),None)
        learn_intent=("یاد بگیر" in low or "یادگیری" in low or "learn" in low or "go learn" in low or "start learning" in low); policy=parse_command(msg); security_words=policy.security; fix_requested=policy.security_action=="fix"
        help_intent=("راهنما" in low or "چطور وصل" in low or "چطور استفاده" in low or "how do i" in low or "how to" in low or "setup" in low)
        if help_intent:
            component="git" if any(x in low for x in ("git","github","گیت","گیت‌هاب")) else ("security" if any(x in low for x in ("امنیت","پن‌تست","pentest")) else ("docker" if "docker" in low else ("python" if "python" in low or "پایتون" in low else "general")))
            return {"type":"help","answer":"راهنمای هوشمند آماده شد.","data":ask_help(msg,component,agent.llm,learner.web)}
        code_words=("برنامه بنویس","کد بنویس","برام برنامه","write a program","write code","program","build an app","create an app"); code_intent=any(x in low for x in code_words)
        if security_words:
            if code_intent:
                language=requested or "Python"; generated=learner.generate_program(msg,language); result=learner.security_assessment_code(generated["code"],language,fix_requested); result["generated_project"]=generated; result["mode"]="pentest_and_fix" if fix_requested else "pentest_report"; return {"type":"security","answer":"Security test completed." if not fix_requested else "Security test, remediation and retest completed.","data":result}
            path=None
            for prefix in ("مسیر:","آدرس:","path:","url:","project:","پروژه:"):
                if prefix in msg: path=msg.split(prefix,1)[1].strip().strip('"').strip("'"); break
            if not path:
                m=re.search(r"https?://[^\s]+",msg)
                if m:path=m.group(0).rstrip(".,)")
            if path:
                if path.lower().startswith(("http://","https://")): result=learner.security_assessment_url(path,r.headers if hasattr(r,"headers") else None); result["note"]="External targets are report-only; remediation is not applied remotely."
                else: result=learner.security_assessment_path(path,fix_requested)
                result["mode"]="external_report" if path.lower().startswith(("http://","https://")) else ("pentest_and_fix" if fix_requested else "pentest_report"); return {"type":"security","answer":"Security test completed for the explicitly supplied target.","data":result}
        if learn_intent: language=requested or "Python"; return {"type":"learning","answer":f"Learning step completed for {canonical_language(language)}.","data":learner.learn_next(language)}
        if code_intent: language=requested or "Python"; return {"type":"code","answer":"Generated program:","data":learner.generate_program(msg,language)}
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
        if r.target_url:return learner.security_assessment_url(r.target_url,r.headers)
        if r.project_path:
            if r.project_path.lower().startswith(("http://","https://")):return learner.security_assessment_url(r.project_path,r.headers)
            return learner.security_assessment_path(r.project_path,r.fix)
        if r.code:return learner.security_assessment_code(r.code,r.language,r.fix)
        return learner.security_scan_latest_generated(r.fix)
    except Exception as e: raise HTTPException(400,str(e))
@app.get("/security/history")
def security_history(limit:int=20): return learner.security.history(limit)
@app.get("/git/repo")
def git_repo(repository:str): return GitHubConnector().repo(repository)
@app.get("/git/tree")
def git_tree(repository:str,ref:str="HEAD"): return GitHubConnector().tree(repository,ref)
@app.get("/git/file")
def git_file(repository:str,path:str,ref:str|None=None): return GitHubConnector().file(repository,path,ref)
@app.get("/git/issues")
def git_issues(repository:str,state:str="open"): return GitHubConnector().issues(repository,state)
@app.get("/git/pulls")
def git_pulls(repository:str,state:str="open"): return GitHubConnector().pull_requests(repository,state)
@app.get("/git/branches")
def git_branches(repository:str): return GitHubConnector().branches(repository)
@app.post("/git/branch")
def git_branch(r:GitRequest): return GitHubConnector().create_branch(r.repository,r.branch or "",r.ref or "main",r.allow_write)
@app.put("/git/file")
def git_update_file(r:GitRequest):
    if not r.path or r.content is None or not r.message: raise HTTPException(400,"path, content and message are required")
    return GitHubConnector().update_file(r.repository,r.path,r.content,r.message,r.branch or "main",r.allow_write)
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
    from .memory import recall; return recall(q,limit)
@app.get("/projects/tasks")
def project_tasks(): return fetch_all("SELECT * FROM project_tasks ORDER BY id")
@app.post("/scheduler/start")
def scheduler_start(r:SchedulerRequest):
    if not 60<=r.interval_seconds<=86400: raise HTTPException(400,"interval_seconds must be 60..86400")
    scheduler.interval_seconds=r.interval_seconds; scheduler.start(r.language); return {"status":"started","language":r.language,"interval_seconds":r.interval_seconds}
@app.get("/scheduler/status")
def scheduler_status(): return {"running":scheduler.running(),"language":scheduler.language,"last_result":scheduler.last_result}
@app.post("/learning/learn")
def learning_learn(r:LearnRequest):
    if not 60<=r.interval_seconds<=86400: raise HTTPException(400,"interval_seconds must be 60..86400")
    scheduler.interval_seconds=r.interval_seconds; scheduler.start(r.language); return {"status":"started","language":r.language,"interval_seconds":r.interval_seconds}
@app.post("/scheduler/stop")
def scheduler_stop(): scheduler.stop(); return {"status":"stopped"}
