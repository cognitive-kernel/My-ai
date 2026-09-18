from __future__ import annotations

import json

from .db import execute, fetch_all
from .llm import OllamaClient


SYSTEM = """You are My-AI, a local programming-focused assistant.
Prioritize correctness over confidence. If you do not know, say so.
When writing Python, prefer clear, tested, maintainable code.
Use the supplied local knowledge when relevant and distinguish it from general reasoning."""


class Agent:
    def __init__(self, llm: OllamaClient | None = None) -> None:
        self.llm = llm or OllamaClient()

    def chat(self, message: str) -> str:
        recent = fetch_all(
            "SELECT role, content FROM conversations ORDER BY id DESC LIMIT 12"
        )[::-1]
        knowledge = fetch_all(
            "SELECT title, content, source_url FROM knowledge ORDER BY id DESC LIMIT 8"
        )
        context = {
            "conversation": recent,
            "knowledge": knowledge,
        }
        prompt = (
            "Use this local context when useful:\n"
            + json.dumps(context, ensure_ascii=False)
            + "\n\nUSER:\n"
            + message
        )
        answer = self.llm.chat(prompt, system=SYSTEM)
        execute("INSERT INTO conversations(role,content) VALUES(?,?)", ("user", message))
        execute("INSERT INTO conversations(role,content) VALUES(?,?)", ("assistant", answer))
        return answer

    def plan_project(self, goal: str) -> list[dict[str, object]]:
        prompt = (
            "Break this software project into an ordered list of 5-15 implementation "
            "tasks. Return JSON array. Each item must have title and description. "
            "Do not claim to have executed anything.\nPROJECT:\n" + goal
        )
        raw = self.llm.chat(prompt)
        try:
            tasks = json.loads(raw)
            if not isinstance(tasks, list):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            tasks = [{"title": "Review generated plan", "description": raw}]

        for item in tasks:
            execute(
                "INSERT INTO project_tasks(project,title,description) VALUES(?,?,?)",
                (goal, str(item.get("title", "Task")), str(item.get("description", ""))),
            )
        return tasks
