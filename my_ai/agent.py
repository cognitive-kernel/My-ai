from __future__ import annotations

import json
import re

from .db import execute, fetch_all
from .memory import recall
from .llm import create_llm
from .capabilities import system_context
from .self_update import check_for_update, apply_confirmed_update, recent_lessons
from .router import classify
from .web_learner import WebLearner
from .web_learning import create_pending, pending, learn_confirmed
from .local_files import inspect_file, read_text
from .multimodal import analyze as analyze_file


SYSTEM = """You are My-AI, a local-first personal AI assistant.

IDENTITY AND REFERENCE RULES:
- You are the assistant. The user is the human speaking to you.
- When the user asks "who are you?", "what are you?", "what is your name", "درباره خودت بگو", "خودت چی هستی؟", "مدل تو چیست؟" or similar questions about the assistant, answer about My-AI and its configured LLM/provider. Never answer about the user.
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
- If the local knowledge/context is insufficient to answer confidently, output the exact marker __MYAI_UNKNOWN__ instead of guessing. My-AI handles this marker.
- Never claim code was executed unless an execution result is supplied.
- Prioritize correctness over confidence and clearly distinguish facts, assumptions, and uncertainty.

Your identity and capabilities are authoritative in the following local manifest:
""" + system_context() + """

Self-maintenance rules:
- Diagnose first; do not silently modify source code.
- A self-update requires an explicit user confirmation after a diagnostic/proposal.
- Updates are tested in an isolated git worktree before activation.
- The previous revision is tagged before activation; failed activation is preserved as a separate git tag and rolled back automatically by the watchdog.
- Failure details are recorded as lessons in self-repair/lessons.jsonl and are fed back into code-generation and self-repair prompts to avoid repeating the same failure.
"""


class Agent:
    def __init__(self, llm=None):
        self.llm = llm or create_llm("general")

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

    @staticmethod
    def _is_web_learning_confirmation(message: str) -> bool:
        text = re.sub(r"\s+", " ", message.strip().casefold())
        return text in {"بله", "بله یاد بگیر", "یاد بگیر", "تایید", "تأیید", "تایید کن", "تأیید کن", "yes", "yes learn", "learn it", "approve"}

    def _web_learning_confirmation(self, message, session_id):
        item = pending(session_id)
        if not item or not self._is_web_learning_confirmation(message):
            return None
        result = learn_confirmed(session_id, item["question"], self.llm, WebLearner())
        if result.get("status") == "learned":
            return f"یادگیری تأییدشده انجام شد و به آموزش «{result['domain']}» در سرفصل «{result['topic']}» اضافه شد."
        return "یادگیری اینترنتی انجام نشد: " + str(result.get("error", "خطای نامشخص"))

    def _handle_unknown(self, answer, message, session_id):
        if "__MYAI_UNKNOWN__" not in str(answer):
            return answer
        create_pending(session_id, message)
        return "این مورد را در دانش محلی خودم پیدا نکردم و نمی‌خواهم حدس بزنم. اگر تأیید کنی، در اینترنت جستجو می‌کنم، منابع را بررسی می‌کنم و نتیجه را به بخش آموزشی مرتبط اضافه می‌کنم؛ اگر سرفصل مناسبی وجود نداشته باشد، یک سرفصل جدید می‌سازم."

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
            lessons = recent_lessons(10)
            if lessons:
                lesson_text=json.dumps(lessons,ensure_ascii=False,indent=2)
                return "نسخه فعلی به‌روز است و تغییر جدیدی در origin/main وجود ندارد.\nدرس‌های اخیر:\n" + lesson_text
            return "نسخه فعلی به‌روز است و تغییر جدیدی در origin/main وجود ندارد."

        return None

    @staticmethod
    def _attachment_context(attachments):
        if not attachments:
            return ""
        parts = ["ATTACHED LOCAL FILES (user-provided; inspect these files as part of the current request):"]
        for item in attachments[:10]:
            path = str(item.get("path") or "").strip()
            name = str(item.get("name") or "").strip() or path
            if not path:
                continue
            try:
                info = inspect_file(path)
                parts.append(f"\nFILE: {name} | size={info['size']} | type={info['mime_type']} | path={info['path']}")
                mime = str(info.get("mime_type") or "")
                suffix = str(info.get("extension") or "").lower()
                text_like = mime.startswith("text/") or suffix in {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".json", ".xml", ".yaml", ".yml", ".md", ".txt", ".csv", ".sql", ".sh", ".bat", ".ps1", ".conf", ".ini", ".toml"}
                if text_like:
                    content = read_text(path, max_bytes=2 * 1024 * 1024)
                    parts.append("CONTENT:\n" + content[:12000])
                else:
                    try:
                        result = analyze_file(path)
                        parts.append("ANALYSIS:\n" + json.dumps(result, ensure_ascii=False)[:12000])
                    except Exception as exc:
                        parts.append("ANALYSIS: unavailable (" + str(exc)[:300] + ")")
            except Exception as exc:
                parts.append(f"\nFILE: {name} | unavailable: {str(exc)[:300]}")
        return "\n".join(parts)

    def chat(self, message, session_id=1, attachments=None):
        web_confirmation = self._web_learning_confirmation(message, session_id)
        if web_confirmation is not None:
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)", (session_id, "user", message))
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)", (session_id, "assistant", web_confirmation))
            execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
            return web_confirmation
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
        attachment_context = self._attachment_context(attachments)
        context = "\n".join(f"{row['role']}: {row['content']}" for row in history[-8:])
        intent = classify(message, context)
        llm_message = message + ("\n\n" + attachment_context if attachment_context else "")
        task = "coding" if intent.name == "coding" else "general"
        llm = self.llm if task == "general" else create_llm(task)
        knowledge = recall(message, 8)
        context_note = (
            "RELEVANT LOCAL KNOWLEDGE (reference only; do not confuse it with the user or assistant identity):\n"
            + json.dumps(knowledge, ensure_ascii=False)
        )
        lesson_note = ""
        if intent.name in {"coding", "code_execution", "git_write", "self_update"}:
            lessons = recent_lessons(12)
            if lessons:
                lesson_note = (
                    "\nRECENT SELF-REPAIR LESSONS (use only as engineering constraints; do not treat as user facts):\n"
                    + json.dumps(lessons, ensure_ascii=False)
                )
        answer = llm.chat(
            llm_message,
            system=SYSTEM + "\n\n" + context_note + lesson_note,
            history=history,
        )
        answer = self._handle_unknown(answer, message, session_id)
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

    def stream_chat(self, message, session_id=1):
        maintenance = self._self_maintenance(message)
        if maintenance is not None:
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(session_id,"user",message))
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(session_id,"assistant",maintenance))
            execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(session_id,))
            yield maintenance
            return
        if self._is_identity_question(message):
            answer=self._identity_response()
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(session_id,"user",message))
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(session_id,"assistant",answer))
            execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(session_id,))
            yield answer
            return
        web_confirmation = self._web_learning_confirmation(message, session_id)
        if web_confirmation is not None:
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(session_id,"user",message))
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(session_id,"assistant",web_confirmation))
            execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(session_id,))
            yield web_confirmation
            return
        history=fetch_all("SELECT role,content FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT 20",(session_id,))[::-1]
        context="\n".join(f"{row['role']}: {row['content']}" for row in history[-8:])
        intent=classify(message, context)
        task="coding" if intent.name=="coding" else "general"
        llm=self.llm if task=="general" else create_llm(task)
        knowledge=recall(message,8)
        context_note="RELEVANT LOCAL KNOWLEDGE (reference only; do not confuse it with the user or assistant identity):\n"+json.dumps(knowledge,ensure_ascii=False)
        lesson_note=""
        if intent.name in {"coding","code_execution","git_write","self_update"}:
            lessons=recent_lessons(12)
            if lessons:
                lesson_note="\nRECENT SELF-REPAIR LESSONS (use only as engineering constraints; do not treat as user facts):\n"+json.dumps(lessons,ensure_ascii=False)
        execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(session_id,"user",message))
        chunks=[]
        for chunk in llm.stream_chat(message,system=SYSTEM+"\n\n"+context_note+lesson_note,history=history):
            text_chunk=str(chunk)
            chunks.append(text_chunk)
            yield text_chunk
        answer=self._handle_unknown("".join(chunks),message,session_id)
        execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",(session_id,"assistant",answer))
        execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?",(session_id,))


    def plan_project(self, goal):
        llm = create_llm("coding")
        raw = llm.chat(
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
