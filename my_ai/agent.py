from __future__ import annotations
import json
from .db import execute,fetch_all
from .memory import recall
from .llm import OllamaClient
SYSTEM="""You are My-AI, a local programming-focused assistant. Prioritize correctness over confidence. Never claim code was executed unless an execution result is supplied. Use local knowledge when relevant and state when evidence is missing."""
class Agent:
    def __init__(self,llm=None): self.llm=llm or OllamaClient()
    def chat(self,message):
        context={"conversation":fetch_all("SELECT role,content FROM conversations ORDER BY id DESC LIMIT 12")[::-1],"knowledge":recall(message,8)}
        answer=self.llm.chat("LOCAL CONTEXT:\n"+json.dumps(context,ensure_ascii=False)+"\n\nUSER:\n"+message,system=SYSTEM)
        execute("INSERT INTO conversations(role,content) VALUES(?,?)",("user",message)); execute("INSERT INTO conversations(role,content) VALUES(?,?)",("assistant",answer))
        return answer
    def plan_project(self,goal):
        raw=self.llm.chat("Break this software project into an ordered JSON array of 5-20 tasks. Each item must contain title, description and acceptance_criteria. PROJECT:\n"+goal)
        try: tasks=json.loads(raw); assert isinstance(tasks,list)
        except (json.JSONDecodeError,AssertionError): tasks=[{"title":"Review generated plan","description":raw,"acceptance_criteria":"Human review"}]
        for x in tasks: execute("INSERT INTO project_tasks(project,title,description) VALUES(?,?,?)",(goal,str(x.get("title","Task")),str(x.get("description",""))))
        return tasks
