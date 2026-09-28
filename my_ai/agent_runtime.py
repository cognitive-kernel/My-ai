from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .agent import Agent as LegacyAgent, SYSTEM
from .db import execute, fetch_all
from .memory import recall
from .llm import create_llm
from .self_update import recent_lessons
from .chat_transport_context import get_attachments


@dataclass
class PreparedChat:
    message: str
    session_id: int
    attachments: list[dict[str, Any]]
    history: list[dict[str, Any]]
    context: str
    intent: Any = None
    task: str = "general"
    llm: Any = None
    llm_message: str = ""
    knowledge: list[dict[str, Any]] | None = None
    enriched_knowledge: list[dict[str, Any]] | None = None
    system: str = SYSTEM
    citation_block: str = ""
    shortcut: str | None = None


class Agent(LegacyAgent):
    """Unified chat pipeline shared by synchronous and streaming chat."""

    def _persist_shortcut(self, ctx: PreparedChat) -> str:
        answer = str(ctx.shortcut or "")
        execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)", (ctx.session_id, "user", ctx.message))
        execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)", (ctx.session_id, "assistant", answer))
        execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (ctx.session_id,))
        return answer

    def _prepare_chat_context(self, message, session_id=1, attachments=None) -> PreparedChat:
        """Single preparation path for chat and stream_chat.

        Order is identical for both transports: web confirmation -> self maintenance ->
        identity -> history/classify/knowledge -> system prompt.
        """
        message = str(message or "")
        normalized_attachments = list(attachments if attachments is not None else get_attachments())[:10]

        web_confirmation = self._web_learning_confirmation(message, session_id)
        if web_confirmation is not None:
            return PreparedChat(message, session_id, normalized_attachments, [], "", shortcut=web_confirmation)

        maintenance = self._self_maintenance(message)
        if maintenance is not None:
            return PreparedChat(message, session_id, normalized_attachments, [], "", shortcut=maintenance)

        if self._is_identity_question(message):
            return PreparedChat(message, session_id, normalized_attachments, [], "", shortcut=self._identity_response())

        history = fetch_all(
            "SELECT role,content FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT 20",
            (session_id,),
        )[::-1]
        context = "\n".join(f"{row['role']}: {row['content']}" for row in history[-8:])
        intent = self._classify(message, context)
        task = "coding" if intent.name == "coding" else "general"
        llm = self.llm if task == "general" else create_llm(task)

        attachment_context = self._attachment_context(normalized_attachments)
        llm_message = message + ("\n\n" + attachment_context if attachment_context else "")

        knowledge = recall(message, 8)
        enriched: list[dict[str, Any]] = []
        for raw_item in knowledge:
            item = dict(raw_item)
            provenance = item.get("provenance")
            if not isinstance(provenance, dict) and item.get("id") is not None:
                provenance = {
                    "citation_id": f"K{item.get('id')}",
                    "source_url": item.get("source_url") or f"local://knowledge/{item.get('id')}",
                    "title": item.get("title") or "local knowledge",
                }
            item["provenance"] = provenance
            item["confidence_label"] = (
                round(float(item["confidence"]), 3)
                if item.get("confidence") is not None and item.get("confidence_calibrated")
                else "uncalibrated"
            )
            enriched.append(item)

        context_note = (
            "RELEVANT LOCAL KNOWLEDGE (verified when marked verified). Cite provenance when making factual claims. "
            "Do not present uncalibrated retrieval as high confidence.\n"
            + json.dumps(knowledge, ensure_ascii=False)
            + "\nRETRIEVAL METADATA:\n"
            + json.dumps(enriched, ensure_ascii=False)
        )
        lesson_note = ""
        if intent.name in {"coding", "code_execution", "git_write", "self_update"}:
            lessons = recent_lessons(12)
            if lessons:
                lesson_note = (
                    "\nRECENT SELF-REPAIR LESSONS (use only as engineering constraints; do not treat as user facts):\n"
                    + json.dumps(lessons, ensure_ascii=False)
                )

        citation_block = self._required_citations(enriched)
        return PreparedChat(
            message=message,
            session_id=session_id,
            attachments=normalized_attachments,
            history=history,
            context=context,
            intent=intent,
            task=task,
            llm=llm,
            llm_message=llm_message,
            knowledge=knowledge,
            enriched_knowledge=enriched,
            system=SYSTEM + "\n\n" + context_note + lesson_note,
            citation_block=citation_block,
        )

    def chat(self, message, session_id=1, attachments=None):
        ctx = self._prepare_chat_context(message, session_id, attachments)
        if ctx.shortcut is not None:
            return self._persist_shortcut(ctx)

        answer = ctx.llm.chat(ctx.llm_message, system=ctx.system, history=ctx.history)
        answer = self._handle_unknown(answer, ctx.message, ctx.session_id)
        if ctx.knowledge and "__MYAI_UNKNOWN__" not in str(answer):
            if ctx.citation_block and not any(
                f"[K{item.get('id')}]" in str(answer) for item in (ctx.enriched_knowledge or [])[:4]
            ):
                answer = answer.rstrip() + ctx.citation_block

        execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)", (ctx.session_id, "user", ctx.message))
        execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)", (ctx.session_id, "assistant", answer))
        execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (ctx.session_id,))
        return answer

    def stream_chat(self, message, session_id=1, attachments=None):
        ctx = self._prepare_chat_context(message, session_id, attachments)
        if ctx.shortcut is not None:
            yield self._persist_shortcut(ctx)
            return

        execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)", (ctx.session_id, "user", ctx.message))

        # Provenance is known before generation; emit it before model chunks so it
        # cannot be lost after the stream terminates.
        if ctx.citation_block and ctx.knowledge:
            yield ctx.citation_block.lstrip() + "\n\n"

        chunks: list[str] = []
        for chunk in ctx.llm.stream_chat(ctx.llm_message, system=ctx.system, history=ctx.history):
            text_chunk = str(chunk)
            chunks.append(text_chunk)
            yield text_chunk

        answer = self._handle_unknown("".join(chunks), ctx.message, ctx.session_id)
        execute("INSERT INTO conversations(session_id,role,content) VALUES(?,?,?)", (ctx.session_id, "assistant", answer))
        execute("UPDATE chat_sessions SET updated_at=CURRENT_TIMESTAMP WHERE id=?", (ctx.session_id,))
