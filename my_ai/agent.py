from __future__ import annotations

import json
import re

from .db import execute, fetch_all
from .memory import recall
from .llm import create_llm
from .capabilities import system_context
from .self_update import check_for_update, apply_confirmed_update, recent_lessons


SYSTEM = """You are My-AI, a local-first personal AI assistant.

IDENTITY AND REFERENCE RULES:
- You are the assistant. The user is the human speaking to you.
- When the user asks "who are you?", "what are you?", "درباره خودت بگو", "خودت چی هستی؟", "مدل تو چیست؟" or similar questions about the assistant, answer about My-AI and its configured LLM/provider. Never answer about the user.
- Words such as «تو»، «خودت»، «درباره خودت» normally refer to the assistant when they occur in an identity/capability question. Words such as «من»، «منو»، «درباره من» refer to the user.
- Do not infer the user's identity, abilities, preferences, or history when the question is explicitly about yourself.
- Distinguish the My-AI application from the underlying LLM: My-AI is the assistant/application; the configured model is its language model backend. Do not claim that My-AI itself is a model if it is not.
- If the exact runtime model/provider is not known, say that it is not known rather than inventing one.

LANGUAGE AND RESPONSE QUALITY:
- Answer in the user's language unless they explicitly request another language.
- For Persian, write natural standard Persian with correct grammar, spelling, punctuation, verb agreement, word order, and نیم‌فاصله where appropriate. Do not translate English syntax word-for-word into Persian.
- Never produce telegraphic fragments when a complete sentence is expected.
- Preserve technical identifiers, code, commands, URLs, file paths, and API names exactly.
- Prefer short, coherent sentences and clear paragraphs. Use headings or bullets when they improve readability.
- Before answering, silently check: (1) what the user is referring to, (2) who "من/تو/خودت" refers to, (3) whether the answer matches the requested language, and (4) whether the sentence structure is grammatical and unambiguous.
- If the request is ambiguous, state the ambiguity briefly and answer the most likely interpretation instead of mixing interpretations.
- Never invent sources, test results, APIs, versions, capabilities, or facts.
- Never claim code was executed unless an execution result is supplied.
- Prioritize correctness over confidence and clearly distinguish facts, assumptions, and uncertainty.

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
    def __init__(self, llm=None):
        self.llm = llm or create_llm()

    @staticmethod
    def _is_identity_question(message: str) -> bool:
        text = re.sub(r"\s+", " ", message.strip().lower())
        patterns = (
            r"\bwho are you\b",
            r"\bwhat are you\b",
            r"\bwhat is your name\b",
            r"\bwhat model are you\b",
            r"\bwhat llm are you\b",
            r"\babout yourself\b",
            r"\bdescribe yourself\b",
            r"درباره\s+خودت",
            r"در مورد\s+خودت",
            r"خودت\s+(چی|چه|کی)\s+(هستی|ای|کسی)",
            r"اسم\s+تو\s+(چیه|چیست)",
            r"مدل\s+تو\s+(چیه|چیست)",
            r"چه\s+مدلی\s+هستی",
            r"تو\s+چه\s+مدلی\s+هستی",
        )
        return any(re.search(pattern, text) for pattern in patterns)

    def _identity_response(self) -> str:
        provider = "OpenAI-compatible" if self.llm.__class__.__name__ == "OpenAICompatibleClient" else "Ollama"
        model = getattr(self.llm, "model", "نامشخص")
        return (
            f"من My-AI هستم؛ دستیار هوش مصنوعی این پروژه. "
            f"مدل زبانی فعال من {model} است و backend فعلی من {provider} است. "
            "من را با کاربر اشتباه نمی‌گیرم: «من» در این پاسخ به خودِ دستیار اشاره دارد."
        )

    def _self_maintenance(self, message):
        low = message.strip().lower()
        inspect_words = (
            "خودت را بررسی کن",
            "خودت رو بررسی کن",
            "خودت را چک کن",
            "خودت رو چک کن",
            "بررسی آپدیت",
            "بررسی خودت",
            "self check",
            "check yourself",
            "check for update",
            "check update",
        )
        confirm_words = (
            "تایید آپدیت",
            "تأیید آپدیت",
            "تایید بروزرسانی",
            "تأیید بروزرسانی",
            "تایید به روزرسانی",
            "تأیید به روزرسانی",
            "confirm update",
            "approve update",
            "apply update",
        )
        if any(x in low for x in confirm_words):
            result = apply_confirmed_update()
            if result.get("status") == "up_to_date":
                return "نسخه فعلی به‌روز است؛ تغییری اعمال نشد."
            if result.get("status") == "blocked":
                return "بروزرسانی اعمال نشد چون تست نسخه جدید شکست خورد.\n" + result.get("details", "")
            return "بروزرسانی تأیید و فعال شد. watchdog سلامت نسخه جدید را بررسی می‌کند و در صورت شکست به snapshot قبلی برمی‌گردد."
        if any(x in low for x in inspect_words):
            result = check_for_update()
            if not result.get("ok"):
                return "بررسی خودکار کامل نشد: " + result.get("error", result.get("reason", "unknown error"))
            if result.get("blocked"):
                return "بررسی متوقف شد چون تغییرات محلی commit نشده وجود دارد."
            if result.get("update_available"):
                return "نسخه جدید در origin/main موجود است. برای اجرای تست ایزوله و فعال‌سازی امن، صریحاً بگو: «تأیید آپدیت»."
            lessons = recent_lessons(5)
            suffix = f"\nآخرین درس‌های ثبت‌شده: {len(lessons)} مورد." if lessons else ""
            return "نسخه فعلی به‌روز است و تغییر جدیدی در origin/main وجود ندارد." + suffix
        return None

    def chat(self, message, session_id=1):
        maintenance = self._self_maintenance(message)
        if maintenance is not None:
            execute(
                "INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",
                (session_id, "user", message),
            )
            execute(
                "INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",
                (session_id, "assistant", maintenance),
            )
            execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
            return maintenance

        if self._is_identity_question(message):
            answer = self._identity_response()
            execute(
                "INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",
                (session_id, "user", message),
            )
            execute(
                "INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",
                (session_id, "assistant", answer),
            )
            execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
            return answer

        history = fetch_all(
            "SELECT role,content FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT 20",
            (session_id,),
        )[::-1]
        knowledge = recall(message, 8)
        context_note = (
            "RELEVANT LOCAL KNOWLEDGE (reference only; do not confuse it with the user or assistant identity):\n"
            + json.dumps(knowledge, ensure_ascii=False)
        )
        answer = self.llm.chat(
            message,
            system=SYSTEM + "\n\n" + context_note,
            history=history,
        )
        execute(
            "INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",
            (session_id, "user", message),
        )
        execute(
            "INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",
            (session_id, "assistant", answer),
        )
        execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
        return answer

    def plan_project(self, goal):
        raw = self.llm.chat(
            "Break this software project into an ordered JSON array of 5-20 tasks. "
            "Each item must contain title, description and acceptance_criteria. PROJECT:\n" + goal
        )
        try:
            tasks = json.loads(raw)
            assert isinstance(tasks, list)
        except (json.JSONDecodeError, AssertionError):
            tasks = [{"title": "Review generated plan", "description": raw, "acceptance_criteria": "Human review"}]
        for x in tasks:
            execute(
                "INSERT INTO project_tasks(project,title,description) VALUES(?,?,?)",
                (goal, str(x.get("title", "Task")), str(x.get("description", ""))),
            )
        return tasks
