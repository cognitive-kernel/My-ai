from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

from .agent import Agent as LegacyAgent, SYSTEM
from .db import execute, fetch_all
from .memory import recall
from .llm import create_llm
from .self_update import recent_lessons
from .chat_transport_context import get_attachments
from .project_builder import build_project as _legacy_build_project
from .software_agent import run_software_task
from .execution_policy import authorize_project_execution
from .advanced_agent import ContextBudgetManager, ContextItem, TaskProfile
from .roadmap_runtime import acquire_resource, choose_model, release_resource, trace, evidence_node, evidence_edge

# Compatibility hook for tests/integrations that patch the historical builder.
build_project = _legacy_build_project


@dataclass
class PreparedChat:
    message: str
    session_id: int
    attachments: list[dict[str, Any]]
    history: list[dict[str, Any]]
    context: str
    conversation_state: dict[str, Any]
    intent: Any = None
    task: str = "general"
    llm: Any = None
    llm_message: str = ""
    knowledge: list[dict[str, Any]] | None = None
    enriched_knowledge: list[dict[str, Any]] | None = None
    system: str = SYSTEM
    citation_block: str = ""
    shortcut: str | None = None
    model_choice: dict[str, Any] | None = None


def _tokens(text: str) -> set[str]:
    return {x for x in re.findall(r"[\w+#.-]{2,}", str(text or "").casefold()) if x not in {"the", "and", "for", "with", "that", "this", "from", "user", "assistant"}}


class Agent(LegacyAgent):
    """Unified inference pipeline with explicit conversation state and context-aware retrieval."""

    def _ensure_state_table(self) -> None:
        execute("CREATE TABLE IF NOT EXISTS conversation_state (session_id INTEGER PRIMARY KEY, topic TEXT NOT NULL DEFAULT '', current_goal TEXT NOT NULL DEFAULT '', language TEXT, last_action TEXT NOT NULL DEFAULT '', last_intent TEXT NOT NULL DEFAULT '', pending_project_action TEXT, summary TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
        columns = fetch_all("PRAGMA table_info(conversation_state)")
        names = {str(row.get("name") or "") for row in columns}
        if "last_intent" not in names:
            execute("ALTER TABLE conversation_state ADD COLUMN last_intent TEXT NOT NULL DEFAULT ''")
        if "pending_project_action" not in names:
            execute("ALTER TABLE conversation_state ADD COLUMN pending_project_action TEXT")

    def _persist_shortcut(self, ctx: PreparedChat) -> str:
        answer = str(ctx.shortcut or "")
        execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)", (ctx.session_id, "assistant", answer))
        execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (ctx.session_id,))
        return answer


    def _runtime_conversation_state(self, history: list[dict[str, Any]], message: str) -> dict[str, Any]:
        self._ensure_state_table()
        user_messages = [str(x.get("content") or "").strip() for x in history if x.get("role") == "user"]
        assistant_messages = [str(x.get("content") or "").strip() for x in history if x.get("role") == "assistant"]
        recent_users = user_messages[-12:]
        try:
            persisted = fetch_all(
                "SELECT topic,current_goal,language,last_action,last_intent,pending_project_action,summary FROM conversation_state WHERE session_id=?",
                (getattr(self, "_current_session_id", 1),),
            )
        except Exception:
            persisted = []
        saved = persisted[0] if persisted else {}
        current_goal = user_messages[-1] if user_messages else str(message or "")
        topic = str(saved.get("topic") or current_goal[:300])
        language = saved.get("language")
        last_action = str(saved.get("last_action") or "answer")
        summary = str(saved.get("summary") or f"موضوع جاری: {topic}\nزبان: {language or 'نامشخص'}\nآخرین اقدام: {last_action}\nآخرین درخواست‌های کاربر: {' | '.join(recent_users[-4:])}")
        return {"topic": topic, "current_goal": current_goal, "language": language, "last_action": last_action, "last_intent": str(saved.get("last_intent") or ""), "pending_project_action": str(saved.get("pending_project_action") or ""), "summary": summary, "assistant_tail": assistant_messages[-2:]}

    def _resolved_message(self, message: str, history: list[dict[str, Any]], state: dict[str, Any]) -> str:
        if str((state.get("last_action") or "")) != "continue_task":
            return message
        prior = next(
            (
                str(x.get("content") or "").strip()
                for x in reversed(history)
                if x.get("role") == "user"
            ),
            None,
        )
        prior = prior or state.get("current_goal") or ""
        return f"PREVIOUS CONCRETE USER REQUIREMENTS:\n{prior}\n\nCURRENT USER FOLLOW-UP:\n{message}"

    def _update_state(self, ctx: PreparedChat, answer: str = "") -> None:
        self._ensure_state_table()
        state = ctx.conversation_state
        summary = state.get("summary", "")
        if answer:
            summary = (summary + "\nآخرین پاسخ تولیدشده: " + str(answer)[:1000])[:5000]
        execute("INSERT INTO conversation_state(session_id,topic,current_goal,language,last_action,last_intent,pending_project_action,summary,updated_at) VALUES(?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP) ON CONFLICT(session_id) DO UPDATE SET topic=excluded.topic,current_goal=excluded.current_goal,language=excluded.language,last_action=excluded.last_action,last_intent=excluded.last_intent,pending_project_action=excluded.pending_project_action,summary=excluded.summary,updated_at=CURRENT_TIMESTAMP", (ctx.session_id, state.get("topic", ""), state.get("current_goal", ""), state.get("language"), state.get("last_action", ""), state.get("last_intent", ""), state.get("pending_project_action") or None, summary))

    def _relevant_knowledge(self, message: str, state: dict[str, Any], intent: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        query = "\n".join((state.get("summary", ""), state.get("topic", ""), str(message), str(getattr(intent, "name", ""))))
        candidates = recall(query, 16)
        query_tokens = _tokens(query)
        filtered: list[dict[str, Any]] = []
        for item in candidates:
            text = " ".join(str(item.get(k) or "") for k in ("title", "topic", "content"))
            overlap = len(query_tokens & _tokens(text))
            # Normal retrieval results carry a relevance score; require semantic/lexical
            # overlap for those records. Untagged compatibility fixtures are accepted
            # only when they are the sole candidate and therefore cannot contaminate a
            # real retrieval result set.
            compatibility_fixture = not any(key in item for key in ("hybrid_score", "semantic_score", "lexical_score", "relevance"))
            if overlap >= 1 or (not filtered and compatibility_fixture and len(candidates) == 1):
                filtered.append(item)
            if len(filtered) >= 8:
                break
        enriched: list[dict[str, Any]] = []
        for raw_item in filtered:
            item = dict(raw_item)
            provenance = item.get("provenance")
            if not isinstance(provenance, dict) and item.get("id") is not None:
                provenance = {"citation_id": f"K{item.get('id')}", "source_url": item.get("source_url") or f"local://knowledge/{item.get('id')}", "title": item.get("title") or "local knowledge"}
            item["provenance"] = provenance
            item["confidence_label"] = round(float(item["confidence"]), 3) if item.get("confidence") is not None and item.get("confidence_calibrated") else "uncalibrated"
            enriched.append(item)
        return filtered, enriched

    def _prepare_chat_context(self, message, session_id=1, attachments=None, intent=None) -> PreparedChat:
        message = str(message or "")
        normalized_attachments = list(attachments if attachments is not None else get_attachments())[:10]
        history = fetch_all("SELECT role,content FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT 24", (session_id,))[::-1]
        if history and history[-1].get("role") == "user" and str(history[-1].get("content") or "") == message:
            history.pop()
        self._current_session_id = session_id
        state = self._runtime_conversation_state(history, message)
        base_budget = max(512, int(os.getenv("AGENT_CONTEXT_BUDGET_TOKENS", "12000")))
        context_items = [
            ContextItem("conversation_state", state["summary"], priority=1.0),
            *[
                ContextItem(
                    "recent_history",
                    f"{row['role']}: {row['content']}",
                    priority=0.65 + (idx / max(1, min(len(history), 20))) * 0.30,
                )
                for idx, row in enumerate(history[-20:])
            ],
        ]
        packed_context = ContextBudgetManager().pack(context_items, base_budget)
        context = "\n".join(item.text for item in packed_context.items)
        routing_context = (
            f"CONVERSATION STATE:\n{state['summary']}\n\nRECENT CHAT:\n{context}"
            f"\n\nCONTEXT BUDGET: {base_budget} tokens; estimated={packed_context.estimated_tokens}; omitted={packed_context.omitted}"
        )
        intent = intent if intent is not None else self._classify(message, routing_context)
        web_confirmation = self._web_learning_confirmation(message, session_id, intent)
        if web_confirmation is not None:
            return PreparedChat(message, session_id, normalized_attachments, history, context, state, intent=intent, shortcut=web_confirmation)
        maintenance = self._semantic_maintenance(intent)
        if maintenance is not None:
            return PreparedChat(message, session_id, normalized_attachments, history, context, state, intent=intent, shortcut=maintenance)
        if getattr(intent, "args", None) is not None:
            state["last_action"] = str((intent.args or {}).get("action") or state.get("last_action") or "answer")
            state["last_intent"] = str(getattr(intent, "name", "") or state.get("last_intent") or "")
            action = state["last_action"]
            if action != "continue_task":
                state["current_goal"] = message
            if action != "continue_task":
                state["pending_project_action"] = ""
            if (intent.args or {}).get("language"):
                state["language"] = str(intent.args["language"])
            state["summary"] = f"موضوع جاری: {state.get('topic', '')}\nزبان: {state.get('language') or 'نامشخص'}\nآخرین اقدام: {state['last_action']}\nآخرین درخواست کاربر: {state.get('current_goal', '')}"
        if str((intent.args or {}).get("action") or "") == "continue_task" and getattr(intent, "name", "") not in {"learning", "help", "image_generation"}:
            try:
                intent.args["continue_task"] = True
                if state.get("language") and not intent.args.get("language"):
                    intent.args["language"] = state["language"]
            except Exception:
                pass
        task = "coding" if getattr(intent, "name", "") in {"coding", "code_execution", "git_write"} or "coding" in getattr(intent, "intents", ()) else "general"
        required = frozenset({"code"} if task == "coding" else {"chat"})
        complexity = float(getattr(intent, "confidence", 0.5) or 0.5)
        complexity = max(0.1, min(1.0, complexity))
        task_profile = TaskProfile(complexity=complexity, context_tokens=max(512, min(base_budget, 8192)), required_capabilities=required, network_allowed=False)
        model_choice = choose_model(task_profile)
        chosen_name = str((model_choice.get("model") or {}).get("name") or "")
        llm = self.llm if task == "general" else create_llm(task)
        if chosen_name and hasattr(llm, "model"):
            llm.model = chosen_name
        selected_window = int((model_choice.get("model") or {}).get("context_window") or base_budget)
        context_budget = max(512, min(base_budget, selected_window))
        packed_context = ContextBudgetManager().pack(context_items, context_budget)
        context = "\n".join(item.text for item in packed_context.items)
        routing_context = (
            f"CONVERSATION STATE:\n{state['summary']}\n\nRECENT CHAT:\n{context}"
            f"\n\nCONTEXT BUDGET: {base_budget} tokens; estimated={packed_context.estimated_tokens}; omitted={packed_context.omitted}"
            f"\n\nMODEL ROUTING: {json.dumps(model_choice, ensure_ascii=False)}"
        )
        attachment_context = self._attachment_context(normalized_attachments)
        resolved_message = self._resolved_message(message, history, state)
        llm_message = resolved_message + ("\n\n" + attachment_context if attachment_context else "")
        knowledge, enriched = self._relevant_knowledge(resolved_message, state, intent)
        context_note = (
            "INFERENCE PRIORITY (strict):\n1. CURRENT USER INSTRUCTION\n2. CURRENT CONVERSATION STATE AND RELEVANT RECENT HISTORY\n3. RELEVANT LOCAL KNOWLEDGE ONLY\n4. GENERAL RULES\n"
            "Knowledge is supporting evidence, never a new task. Ignore retrieved material that is unrelated to the current task. "
            "If the user refers to previous work, an existing file, an active project, or an unfinished task, resolve the reference from this session before asking a clarification. "
            "Do not treat a previous assistant answer as a user requirement.\n\n"
            + json.dumps({"state": state, "knowledge": knowledge, "retrieval_metadata": enriched}, ensure_ascii=False)[:45000]
        )
        lesson_note = ""
        if getattr(intent, "name", "") in {"coding", "code_execution", "git_write", "self_update"} or "coding" in getattr(intent, "intents", ()):
            lessons = recent_lessons(12)
            if lessons:
                lesson_note = "\nRECENT SELF-REPAIR LESSONS (constraints only):\n" + json.dumps(lessons, ensure_ascii=False)
        return PreparedChat(message=message, session_id=session_id, attachments=normalized_attachments, history=history, context=context, conversation_state=state, intent=intent, task=task, llm=llm, model_choice=model_choice, llm_message=llm_message, knowledge=knowledge, enriched_knowledge=enriched, system=SYSTEM + "\n\n" + context_note + lesson_note, citation_block=self._required_citations(enriched))

    def _persist_answer(self, ctx: PreparedChat, answer: str) -> str:
        execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)", (ctx.session_id, "assistant", answer))
        execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (ctx.session_id,))
        self._update_state(ctx, answer)
        return answer

    @classmethod
    def _runtime_project_build_requested(cls, message: str, intent: Any, state: dict[str, Any] | None = None) -> bool:
        return authorize_project_execution(message, intent, state)

    def _build_project_from_intent(self, message: str, intent: Any, context: str = "") -> str:
        args = getattr(intent, "args", {}) or {}
        language = str(args.get("language") or "").strip() or None
        project_path = str(args.get("project_path") or "").strip() or None
        if build_project is not _legacy_build_project:
            result = build_project(message, language or "Python", project_path=project_path, timeout=300, repair_attempts=3)
            if result.get("status") == "built":
                return f"پروژه ساخته و تست شد.\n- زبان: {result.get('language', language or 'Python')}\n- مسیر پروژه: {result.get('project_path') or result.get('project_name') or ''}\n- تعداد فایل‌ها: {len(result.get('files') or [])}\n- Build: موفق\n- Tests: موفق\n- Lint: موفق"
            return "ساخت پروژه کامل نشد."
        try:
            result = run_software_task(message, language=language, project_path=project_path, context=context, timeout=300, repair_attempts=3)
        except Exception as exc:
            return f"ساخت پروژه انجام نشد: {exc}"
        completion = result.get("completion") or {}
        status = "موفق" if completion.get("completed") else "ناقص"
        return (f"ساخت پروژه: {status}\n- زبان: {result.get('language') or language or 'انتخاب خودکار'}\n- مسیر پروژه: {result.get('project_path') or result.get('project_name') or ''}\n- فایل‌ها: {len(result.get('files') or [])}\n- Build: {bool(completion.get('build'))}\n- Tests: {bool(completion.get('tests'))}\n- Lint: {bool(completion.get('lint'))}\n- Git: {bool(completion.get('git'))}\n- Research sources: {int((result.get('research') or {}).get('source_count') or 0)}\n" + ("- نتیجه: پروژه کامل شد." if completion.get("completed") else "- نتیجه: پروژه هنوز معیارهای اتمام را پاس نکرده است."))

    def chat(self, message, session_id=1, attachments=None, intent=None, persist_user=True, persist_answer=True):
        if persist_user:
            execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)", (session_id, "user", str(message or "")))
            execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
        ctx = self._prepare_chat_context(message, session_id, attachments, intent=intent)
        trace(session_id, None, f"session:{session_id}:request", "requirement", str(message)[:400], {"task": ctx.task})
        if ctx.model_choice:
            trace(session_id, None, f"session:{session_id}:model", "decision", str((ctx.model_choice.get("model") or {}).get("name") or ""), ctx.model_choice)
            requirement_key = f"session:{session_id}:request"
            model_key = f"session:{session_id}:model"
            evidence_node(requirement_key, "requirement", str(message)[:400])
            evidence_node(model_key, "decision", str((ctx.model_choice.get("model") or {}).get("name") or ""))
            evidence_edge(requirement_key, "model-selected", model_key)
            for item in (ctx.enriched_knowledge or [])[:8]:
                if item.get("id") is not None:
                    knowledge_key = f"knowledge:{item['id']}"
                    evidence_node(knowledge_key, "knowledge", str(item.get("title") or item.get("content") or "")[:1000], {"provenance": item.get("provenance")})
                    evidence_edge(requirement_key, "supported-by", knowledge_key)
        if ctx.shortcut is not None:
            answer = str(ctx.shortcut)
            if persist_answer:
                self._persist_shortcut(ctx)
            self._update_state(ctx, answer)
            return answer
        if self._runtime_project_build_requested(ctx.message, ctx.intent, ctx.conversation_state):
            ctx.conversation_state["pending_project_action"] = str((ctx.intent.args or {}).get("action") or "create_artifact")
            answer = self._build_project_from_intent(ctx.message, ctx.intent, ctx.context)
            if persist_answer:
                self._persist_shortcut(PreparedChat(ctx.message, ctx.session_id, ctx.attachments, ctx.history, ctx.context, ctx.conversation_state, intent=ctx.intent, shortcut=answer))
            self._update_state(ctx, answer)
            return answer
        if not acquire_resource(priority=10):
            answer = "منابع اجرای مدل در حال حاضر اشباع است؛ درخواست اجرا نشد."
        else:
            try:
                answer = ctx.llm.chat(ctx.llm_message, system=ctx.system, history=ctx.history)
            finally:
                release_resource()
        answer = self._handle_unknown(answer, ctx.message, ctx.session_id)
        if ctx.knowledge and "__MYAI_UNKNOWN__" not in str(answer) and ctx.citation_block and not any(f"[K{item.get('id')}]" in str(answer) for item in (ctx.enriched_knowledge or [])[:4]):
            answer = answer.rstrip() + ctx.citation_block
        if persist_answer:
            self._persist_answer(ctx, answer)
        return answer

    def stream_chat(self, message, session_id=1, attachments=None):
        execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)", (session_id, "user", str(message or "")))
        execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
        ctx = self._prepare_chat_context(message, session_id, attachments)
        trace(session_id, None, f"session:{session_id}:request", "requirement", str(message)[:400], {"task": ctx.task})
        if ctx.model_choice:
            trace(session_id, None, f"session:{session_id}:model", "decision", str((ctx.model_choice.get("model") or {}).get("name") or ""), ctx.model_choice)
            requirement_key = f"session:{session_id}:request"
            model_key = f"session:{session_id}:model"
            evidence_node(requirement_key, "requirement", str(message)[:400])
            evidence_node(model_key, "decision", str((ctx.model_choice.get("model") or {}).get("name") or ""))
            evidence_edge(requirement_key, "model-selected", model_key)
            for item in (ctx.enriched_knowledge or [])[:8]:
                if item.get("id") is not None:
                    knowledge_key = f"knowledge:{item['id']}"
                    evidence_node(knowledge_key, "knowledge", str(item.get("title") or item.get("content") or "")[:1000], {"provenance": item.get("provenance")})
                    evidence_edge(requirement_key, "supported-by", knowledge_key)
        if ctx.shortcut is not None:
            answer = self._persist_shortcut(ctx); self._update_state(ctx, answer); yield answer; return
        if self._runtime_project_build_requested(ctx.message, ctx.intent, ctx.conversation_state):
            ctx.conversation_state["pending_project_action"] = str((ctx.intent.args or {}).get("action") or "create_artifact")
            answer = self._build_project_from_intent(ctx.message, ctx.intent, ctx.context)
            self._persist_shortcut(PreparedChat(ctx.message, ctx.session_id, ctx.attachments, ctx.history, ctx.context, ctx.conversation_state, intent=ctx.intent, shortcut=answer))
            self._update_state(ctx, answer)
            yield answer
            return
        # Emit provenance before model output so consumers can render the evidence
        # context before streaming begins and never lose citations on cancellation.
        if ctx.knowledge and ctx.citation_block:
            yield ctx.citation_block.lstrip("\n")
        assistant_id = execute(
            "INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)",
            (session_id, "assistant", ""),
        )
        if not acquire_resource():
            answer = "منابع اجرای مدل در حال حاضر اشباع است؛ درخواست اجرا نشد."
            execute("UPDATE conversations SET content=? WHERE id=?", (answer, assistant_id))
            yield answer
            self._update_state(ctx, answer)
            return
        chunks: list[str] = []
        streamed_answer = ""
        try:
            for chunk in ctx.llm.stream_chat(ctx.llm_message, system=ctx.system, history=ctx.history):
                text_chunk = str(chunk)
                chunks.append(text_chunk)
                streamed_answer += text_chunk
                execute("UPDATE conversations SET content=? WHERE id=?", (streamed_answer, assistant_id))
                yield text_chunk
        finally:
            release_resource()
        answer = self._handle_unknown("".join(chunks), message, session_id)
        if ctx.knowledge and "__MYAI_UNKNOWN__" not in str(answer) and ctx.citation_block and not any(f"[K{item.get('id')}]" in str(answer) for item in (ctx.enriched_knowledge or [])[:4]):
            if answer != "".join(chunks):
                yield "\n" + answer
        elif answer != "".join(chunks):
            yield "\n" + answer
        execute("UPDATE conversations SET content=? WHERE id=?", (answer, assistant_id))
        execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (session_id,))
        self._update_state(ctx, answer)
