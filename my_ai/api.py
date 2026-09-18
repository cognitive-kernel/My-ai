from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

from .agent import Agent
from .config import settings
from .db import fetch_all, init_db
from .learner import LearningEngine


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="My-AI",
    version="0.1.0",
    description="Local-first personal learning and coding agent.",
    lifespan=lifespan,
)

agent = Agent()
learner = LearningEngine()


class ChatRequest(BaseModel):
    message: str


class URLRequest(BaseModel):
    url: HttpUrl


class ProjectRequest(BaseModel):
    goal: str


class CodeRequest(BaseModel):
    code: str


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "model": settings.ollama_model}


@app.post("/chat")
def chat(request: ChatRequest) -> dict[str, str]:
    try:
        return {"answer": agent.chat(request.message)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/learn/url")
def learn_url(request: URLRequest) -> dict[str, object]:
    try:
        return learner.study_url(str(request.url))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/learning/python/start")
def start_python() -> dict[str, object]:
    return learner.start_python()


@app.get("/learning/status")
def learning_status() -> list[dict[str, object]]:
    return learner.status()


@app.post("/learning/practice")
def practice(request: ChatRequest) -> dict[str, object]:
    try:
        return learner.practice(request.message)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/code/run")
def code_run(request: CodeRequest) -> dict[str, object]:
    return learner.validate_code(request.code)


@app.post("/projects/plan")
def project_plan(request: ProjectRequest) -> dict[str, object]:
    try:
        return {"tasks": agent.plan_project(request.goal)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/memory/knowledge")
def knowledge() -> list[dict[str, object]]:
    return fetch_all("SELECT * FROM knowledge ORDER BY id DESC")


@app.get("/projects/tasks")
def project_tasks() -> list[dict[str, object]]:
    return fetch_all("SELECT * FROM project_tasks ORDER BY id")
