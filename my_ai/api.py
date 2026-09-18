from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI,HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,HttpUrl
from .agent import Agent
from .config import settings
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
class LanguageRequest(BaseModel): language:str="Python"
class SchedulerRequest(BaseModel): language:str="Python"; interval_seconds:int=3600
@app.get("/",response_class=HTMLResponse)
def home(): return page()
@app.get("/health")
def health(): return {"status":"ok","model":settings.ollama_model}
@app.post("/chat")
def chat(r:ChatRequest):
    try:return {"answer":agent.chat(r.message)}
    except Exception as e:raise HTTPException(502,str(e))
@app.post("/learn/url")
def learn_url(r:URLRequest):
    try:return learner.study_url(str(r.url),r.topic)
    except Exception as e:raise HTTPException(400,str(e))
@app.post("/learning/start")
def learning_start(r:LanguageRequest): return learner.start(r.language)
@app.post("/learning/step")
def learning_step(r:LanguageRequest):
    try:return learner.autonomous_step(r.language)
    except Exception as e:raise HTTPException(502,str(e))
@app.get("/learning/status")
def learning_status(language:str|None=None): return learner.status(language)
@app.post("/learning/practice")
def practice(r:ChatRequest):
    try:return learner.practice(r.message)
    except Exception as e:raise HTTPException(502,str(e))
@app.post("/code/run")
def code_run(r:CodeRequest): return learner.validate_code(r.code)
@app.post("/projects/plan")
def project_plan(r:ProjectRequest):
    try:return {"tasks":agent.plan_project(r.goal)}
    except Exception as e:raise HTTPException(502,str(e))
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
@app.post("/scheduler/stop")
def scheduler_stop(): scheduler.stop(); return {"status":"stopped"}
