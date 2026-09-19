from __future__ import annotations
import json
from .db import execute,fetch_all
from .memory import recall
from .llm import OllamaClient
from .capabilities import system_context
from .self_update import check_for_update, apply_confirmed_update, recent_lessons

SYSTEM="""You are My-AI, a local-first personal AI assistant. Prioritize correctness over confidence. Never claim code was executed unless an execution result is supplied. Use local knowledge when relevant and state when evidence is missing.

Your identity and capabilities are authoritative in the following local manifest:
""" + system_context() + """

Self-maintenance rules:
- Diagnose first; do not silently modify source code.
- A self-update requires an explicit user confirmation after a diagnostic/proposal.
- Updates are tested in an isolated git worktree before activation.
- The previous revision is tagged before activation; failed activation is preserved as a separate git tag and rolled back automatically by the watchdog.
- Failure details are recorded as lessons in data/self_update/lessons.jsonl so they can be reviewed and used to avoid repeating the same failure.
"""

class Agent:
    def __init__(self,llm=None): self.llm=llm or OllamaClient()

    def _self_maintenance(self, message):
        low=message.strip().lower()
        inspect_words=("خودت را بررسی کن","خودت رو بررسی کن","خودت را چک کن","خودت رو چک کن","بررسی آپدیت","بررسی خودت","self check","check yourself","check for update","check update")
        confirm_words=("تایید آپدیت","تأیید آپدیت","تایید بروزرسانی","تأیید بروزرسانی","تایید به روزرسانی","تأیید به روزرسانی","confirm update","approve update","apply update")
        if any(x in low for x in confirm_words):
            result=apply_confirmed_update()
            if result.get("status")=="up_to_date":
                return "نسخه فعلی به‌روز است؛ تغییری اعمال نشد."
            if result.get("status")=="blocked":
                return "بروزرسانی اعمال نشد چون تست نسخه جدید شکست خورد.\n"+result.get("details","")
            return "بروزرسانی تأیید و فعال شد. watchdog سلامت نسخه جدید را بررسی می‌کند و در صورت شکست به snapshot قبلی برمی‌گردد."
        if any(x in low for x in inspect_words):
            result=check_for_update()
            if not result.get("ok"):
                return "بررسی خودکار کامل نشد: "+result.get("error",result.get("reason","unknown error"))
            if result.get("blocked"):
                return "بررسی متوقف شد چون تغییرات محلی commit نشده وجود دارد."
            if result.get("update_available"):
                return "نسخه جدید در origin/main موجود است. برای اجرای تست ایزوله و فعال‌سازی امن، صریحاً بگو: «تأیید آپدیت»."
            lessons=recent_lessons(5)
            suffix=f"\nآخرین درس‌های ثبت‌شده: {len(lessons)} مورد." if lessons else ""
            return "نسخه فعلی به‌روز است و تغییر جدیدی در origin/main وجود ندارد."+suffix
        return None

    def chat(self,message,session_id=1):
        maintenance=self._self_maintenance(message)
        if maintenance is not None:
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(session_id,"user",message))
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(session_id,"assistant",maintenance))
            execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(session_id,))
            return maintenance
        context={"conversation":fetch_all("SELECT role,content FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT 20",(session_id,))[::-1],"knowledge":recall(message,8)}
        answer=self.llm.chat("LOCAL CONTEXT:\n"+json.dumps(context,ensure_ascii=False)+"\n\nUSER:\n"+message,system=SYSTEM)
        execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(session_id,"user",message)); execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(session_id,"assistant",answer)); execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(session_id,))
        return answer

    def plan_project(self,goal):
        raw=self.llm.chat("Break this software project into an ordered JSON array of 5-20 tasks. Each item must contain title, description and acceptance_criteria. PROJECT:\n"+goal)
        try: tasks=json.loads(raw); assert isinstance(tasks,list)
        except (json.JSONDecodeError,AssertionError): tasks=[{"title":"Review generated plan","description":raw,"acceptance_criteria":"Human review"}]
        for x in tasks: execute("INSERT INTO project_tasks(project,title,description) VALUES(?,?,?)",(goal,str(x.get("title","Task")),str(x.get("description",""))))
        return tasks
