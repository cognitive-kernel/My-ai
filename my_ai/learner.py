from __future__ import annotations

import json

from .curriculum import PYTHON_CURRICULUM, next_topic
from .db import execute, fetch_all
from .executor import run_python
from .llm import OllamaClient
from .web_learner import WebLearner


class LearningEngine:
    def __init__(self, llm: OllamaClient | None = None) -> None:
        self.llm = llm or OllamaClient()
        self.web = WebLearner()

    def study_url(self, url: str, topic: str = "Python") -> dict[str, object]:
        title, text = self.web.fetch(url)
        prompt = (
            "You are a meticulous programming teacher. Extract durable, technically "
            "accurate knowledge from the following source. Focus on Python concepts, "
            "APIs, syntax, constraints, examples and common mistakes. Return a concise "
            "structured study note. Do not invent facts.\n\nSOURCE:\n" + text
        )
        note = self.llm.chat(prompt)
        execute(
            "INSERT INTO knowledge(topic,title,content,source_url) VALUES(?,?,?,?)",
            (topic, title, note, url),
        )
        return {"title": title, "source_url": url, "knowledge": note}

    def start_python(self) -> dict[str, object]:
        rows = fetch_all(
            "SELECT topic FROM learning_sessions WHERE language='Python' AND status='completed'"
        )
        completed = {str(r["topic"]) for r in rows}
        topic = next_topic(completed)
        if not topic:
            return {"status": "completed", "message": "Python curriculum is complete."}

        execute(
            "INSERT INTO learning_sessions(language,topic,status,notes) VALUES(?,?,?,?)",
            ("Python", str(topic["topic"]), "started", json.dumps(topic, ensure_ascii=False)),
        )
        return {"status": "started", "topic": topic}

    def practice(self, task: str) -> dict[str, object]:
        prompt = (
            "Create one Python exercise for this learning task. Return JSON with "
            "keys description, starter_code, expected_behavior.\nTask: " + task
        )
        raw = self.llm.chat(prompt)
        return {"exercise": raw}

    def validate_code(self, code: str) -> dict[str, object]:
        result = run_python(code)
        passed = result.return_code == 0 and not result.timed_out
        execute(
            "INSERT INTO experiments(language,code,output,error,passed) VALUES(?,?,?,?,?)",
            ("Python", code, result.output, result.error, int(passed)),
        )
        return {
            "passed": passed,
            "output": result.output,
            "error": result.error,
            "return_code": result.return_code,
            "timed_out": result.timed_out,
        }

    def status(self) -> list[dict[str, object]]:
        return fetch_all(
            "SELECT id, language, topic, status, score, notes, created_at "
            "FROM learning_sessions ORDER BY id DESC"
        )
