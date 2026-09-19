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
from .help import page as help_page, ask_help, local_help_html, apply_help_update
from .git_connector import GitHubConnector

scheduler=StudyScheduler()
@asynccontextmanager
async def lifespan(_):
    init_db()
    active=fetch_all("SELECT language FROM learning_sessions WHERE status='started' ORDER BY id DESC LIMIT 1")
    if active: scheduler.start(active[0]["language"])
    yield
    scheduler.stop()
app=FastAPI(title="My-AI",version="0.2.0",description="Local-first personal learning and coding agent.",lifespan=lifespan)
agent=Agent(); learner=LearningEngine()
class ChatRequest(BaseModel): message:str; session_id:int|None=None
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
@app.get("/chat/sessions")
def chat_sessions(): return {"sessions":fetch_all("SELECT id,title,kind,language,pinned,created_at,updated_at FROM chat_sessions ORDER BY pinned DESC,updated_at DESC,id DESC")}
@app.patch("/chat/sessions/{session_id}")
def update_chat_session(session_id:int,r:ChatRequest):
    rows=fetch_all("SELECT id FROM chat_sessions WHERE id=?",(session_id,))
    if not rows: raise HTTPException(404,"Chat session not found")
    payload=r.message.strip()
    if payload:
        execute("UPDATE chat_sessions SET title=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(payload[:80],session_id))
    return {"status":"updated","id":session_id}
@app.post("/chat/sessions/{session_id}/pin")
def pin_chat_session(session_id:int):
    rows=fetch_all("SELECT id,pinned FROM chat_sessions WHERE id=?",(session_id,))
    if not rows: raise HTTPException(404,"Chat session not found")
    new_value=0 if rows[0]["pinned"] else 1
    execute("UPDATE chat_sessions SET pinned=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(new_value,session_id))
    return {"id":session_id,"pinned":bool(new_value)}
@app.delete("/chat/sessions/{session_id}")
def delete_chat_session(session_id:int):
    rows=fetch_all("SELECT id FROM chat_sessions WHERE id=?",(session_id,))
    if not rows: raise HTTPException(404,"Chat session not found")
    execute("DELETE FROM conversations WHERE session_id=?",(session_id,))
    execute("DELETE FROM chat_sessions WHERE id=?",(session_id,))
    return {"status":"deleted","id":session_id}
@app.post("/chat/sessions")
def create_chat_session(r:ChatRequest):
    sid=execute("INSERT INTO chat_sessions(title) VALUES(?)",((r.message or "گفتگوی جدید").strip()[:60],)); return {"id":sid}
@app.get("/chat/history")
def chat_history(limit:int=100,session_id:int|None=None):
    limit=max(1,min(limit,500))
    if session_id is None: rows=fetch_all("SELECT role,content,created_at FROM conversations ORDER BY id DESC LIMIT ?",(limit,))
    else: rows=fetch_all("SELECT role,content,created_at FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT ?",(session_id,limit))
    rows.reverse(); return {"messages":rows}

@app.get("/help/updates")
def help_updates(status:str="pending"): return fetch_all("SELECT * FROM help_updates WHERE status=? ORDER BY id DESC",(status,))
@app.post("/help/ask")
def help_ask(r:ChatRequest):
    try:
        low=r.message.lower(); component="git" if any(x in low for x in ("git","github","گیت","گیت‌هاب")) else ("security" if any(x in low for x in ("امنیت","پن‌تست","pentest")) else ("docker" if "docker" in low else ("python" if "python" in low or "پایتون" in low else "general")))
        return ask_help(r.message,component,agent.llm,learner.web)
    except Exception as e: raise HTTPException(502,str(e))
@app.get("/help/local")
def help_local(component:str="chat"):
    return HTMLResponse("<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'><title>My-AI — راهنمای محلی</title><style>body{font-family:Tahoma;max-width:900px;margin:30px auto;padding:20px;line-height:2;background:#f3f4f6}main{background:#fff;padding:25px;border-radius:14px}</style><main>"+local_help_html(component)+"</main></html>")

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
        learn_intent=("یاد بگیر" in low or "یادگیری" in low or "learn" in low or "go learn" in low or "start learning" in low); sid=r.session_id or execute("INSERT INTO chat_sessions(title,kind,language) VALUES(?,?,?)",(msg[:60] or "گفتگوی جدید","learning" if learn_intent else "chat",requested)); policy=parse_command(msg); security_words=policy.security; fix_requested=policy.security_action=="fix"
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
        if learn_intent:
            language=requested or "Python"
            language=canonical_language(language)
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(sid,"user",msg))
            scheduler.interval_seconds=3600
            scheduler.start(language)
            answer=f"یادگیری {language} در پس‌زمینه شروع شد."
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(sid,"assistant",answer)); execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(sid,))
            return {"type":"learning","answer":answer,"data":{"status":"started","language":language,"interval_seconds":3600,"session_id":sid},"session_id":sid}
        if code_intent: language=requested or "Python"; return {"type":"code","answer":"Generated program:","data":learner.generate_program(msg,language)}
        return {"type":"chat","answer":agent.chat(msg,sid),"session_id":sid}
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
@app.post("/git/login")
def git_login():
    try:
        if not GitHubConnector.gh_available():
            raise HTTPException(503,"GitHub CLI (gh) نصب نیست. GitHub CLI را نصب کنید و دوباره تلاش کنید.")
        authenticated=GitHubConnector.gh_logged_in()
        if not authenticated:
            GitHubConnector.gh_login()
            return {"authenticated":False,"pending":True,"token_source":GitHubConnector.token_source(),"message":"مرورگر برای ورود GitHub باز شد. بعد از تأیید، «بررسی اتصال» را بزنید."}
        return {"authenticated":True,"pending":False,"token_source":GitHubConnector.token_source(),"message":"ورود GitHub قبلاً انجام شده است."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502,str(e))

@app.post("/git/logout")
def git_logout():
    try:
        GitHubConnector.save_token("")
        exe=GitHubConnector._gh_executable()
        if exe:
            import subprocess
            r=subprocess.run([exe,"auth","logout","--hostname","github.com","--yes"],capture_output=True,text=True,timeout=30,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            if r.returncode != 0:
                raise RuntimeError((r.stderr or r.stdout or "GitHub logout failed").strip())
        return {"authenticated":False,"message":"از GitHub خارج شدی."}
    except Exception as e:
        raise HTTPException(502,str(e))

@app.get("/git/connection")
def git_connection():
    try:
        data=GitHubConnector().repo("cognitive-kernel/My-ai")
        return {"connected":True,"authenticated":GitHubConnector.token_status(),"repository":data.get("full_name"),"private":data.get("private",False)}
    except Exception as e:
        return {"connected":False,"authenticated":bool(__import__("os").getenv("GITHUB_TOKEN")),"error":str(e)}
@app.post("/git/token")
def git_token(r:ChatRequest):
    token=r.message.strip()
    if token and len(token)<20: raise HTTPException(400,"توکن GitHub نامعتبر است.")
    try:
        if not token:
            GitHubConnector.save_token("")
            return {"saved":False,"authenticated":False}
        GitHubConnector.save_token(token)
        c=GitHubConnector(token=token)
        try:
            repo_data=c.repo("cognitive-kernel/My-ai")
            identity=repo_data.get("owner") or {}
        except Exception as e:
            if isinstance(e, __import__("my_ai.git_connector", fromlist=["GitHubAPIError"]).GitHubAPIError):
                if e.status_code == 401:
                    GitHubConnector.save_token("")
                    raise HTTPException(401, f"GitHub Token رد شد: {e.message}")
                if e.status_code == 403:
                    raise HTTPException(403, f"GitHub Token احراز هویت شد اما GitHub دسترسی این درخواست را رد کرد: {e.message}")
                raise HTTPException(502, f"GitHub API خطای {e.status_code} داد: {e.message}")
            raise HTTPException(502, f"اتصال به GitHub برقرار نشد: {e}")
        return {
            "saved":True,
            "authenticated":True,
            "login":identity.get("login"),
            "name":identity.get("name"),
        }
    except HTTPException:
        raise
    except Exception as e:
        if isinstance(e, __import__("my_ai.git_connector", fromlist=["GitHubAPIError"]).GitHubAPIError):
            raise HTTPException(e.status_code if e.status_code in (400,401,403,404,409,422,429) else 502, f"GitHub API: {e.message}")
        raise HTTPException(502,f"GitHub connector error: {e}")

@app.delete("/git/token")
def delete_git_token():
    try:
        GitHubConnector.save_token("")
        return {"saved":False,"authenticated":False}
    except Exception as e: raise HTTPException(500,str(e))

@app.get("/git/whoami")
def git_whoami():
    try:
        c=GitHubConnector()
        token_source=GitHubConnector.token_source()
        if token_source == "none":
            raise HTTPException(401,"GitHub Token تنظیم نشده است.")
        data=c.repo("cognitive-kernel/My-ai")
        identity=data.get("owner") or {}
        return {"authenticated":True,"login":identity.get("login"),"name":identity.get("name"),"token_source":token_source}
    except HTTPException: raise
    except Exception as e:
        if isinstance(e, __import__("my_ai.git_connector", fromlist=["GitHubAPIError"]).GitHubAPIError):
            raise HTTPException(e.status_code if e.status_code in (401,403,404,429) else 502, f"GitHub API: {e.message}")
        raise HTTPException(502,f"اتصال به GitHub برقرار نشد: {e}")

@app.get("/git/token/diagnostics")
def git_token_diagnostics():
    try:
        c=GitHubConnector()
        d=c.token_diagnostics()
        return {"authenticated":False,**d}
    except Exception as e:
        raise HTTPException(500,f"GitHub token diagnostics error: {e}")

@app.get("/git/check")
def git_check(repository:str="cognitive-kernel/My-ai"):
    c=GitHubConnector()
    token_source=GitHubConnector.token_source()
    if token_source == "none":
        return {"authenticated":False,"repository":repository,"status":"no_token","message":"GitHub Token تنظیم نشده است."}
    try:
        data=c.repo(repository)
        identity=data.get("owner") or {}
    except Exception as e:
        if isinstance(e, __import__("my_ai.git_connector", fromlist=["GitHubAPIError"]).GitHubAPIError):
            if e.status_code == 401:
                return {"authenticated":False,"repository":repository,"status":"invalid_token","http_status":401,"token_source":token_source,"github_message":e.message,"message":"GitHub این Token را رد کرد؛ ممکن است revoke شده یا واقعاً نامعتبر باشد."}
            if e.status_code == 403:
                return {"authenticated":False,"repository":repository,"status":"auth_forbidden","http_status":403,"token_source":token_source,"github_message":e.message,"message":"GitHub Token شناخته شد، اما سیاست یا دسترسی GitHub این درخواست را رد کرد."}
            return {"authenticated":False,"repository":repository,"status":"github_auth_error","http_status":e.status_code,"token_source":token_source,"github_message":e.message,"message":f"GitHub خطای {e.status_code} در احراز هویت برگرداند."}
        return {"authenticated":False,"repository":repository,"status":"network_error","token_source":token_source,"message":f"اتصال به GitHub برقرار نشد: {e}"}
    try:
        return {
            "authenticated":True,
            "repository":repository,
            "status":"ok",
            "login":identity.get("login"),
            "private":bool(data.get("private")),
            "permissions":data.get("permissions") or {},
            "message":"Token معتبر است و به مخزن دسترسی دارد.",
        }
    except Exception as e:
        if isinstance(e, __import__("my_ai.git_connector", fromlist=["GitHubAPIError"]).GitHubAPIError):
            if e.status_code == 404:
                return {"authenticated":True,"repository":repository,"status":"repo_forbidden_or_missing","http_status":404,"login":identity.get("login"),"github_message":e.message,"message":"Token معتبر است، اما GitHub این مخزن را برای این Token قابل دسترسی نمی‌داند."}
            if e.status_code == 403:
                return {"authenticated":True,"repository":repository,"status":"repo_forbidden","http_status":403,"login":identity.get("login"),"github_message":e.message,"message":"Token معتبر است، اما GitHub دسترسی این مخزن یا permission لازم را رد کرد."}
            return {"authenticated":True,"repository":repository,"status":"github_error","http_status":e.status_code,"login":identity.get("login"),"github_message":e.message,"message":f"GitHub خطای {e.status_code} داد."}
        return {"authenticated":True,"repository":repository,"status":"network_error","login":identity.get("login"),"message":f"اتصال به GitHub برقرار نشد: {e}"}

@app.get("/git/repo")
def git_repo(repository:str):
    try:
        data=GitHubConnector().repo(repository)
        data["connected"]=True
        data["authenticated"]=GitHubConnector.token_status()
        return data
    except Exception as e:
        msg=str(e)
        code=404 if "GitHub API 404" in msg else 502
        raise HTTPException(code,msg)
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
def scheduler_status(): return scheduler.status()
@app.post("/learning/learn")
def learning_learn(r:LearnRequest):
    if not 60<=r.interval_seconds<=86400: raise HTTPException(400,"interval_seconds must be 60..86400")
    scheduler.interval_seconds=r.interval_seconds; scheduler.start(r.language); return {"status":"started","language":r.language,"interval_seconds":r.interval_seconds}
@app.post("/scheduler/stop")
def scheduler_stop(): scheduler.stop(); return {"status":"stopped"}
