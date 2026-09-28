from dataclasses import dataclass
from typing import Any

@dataclass
class ChatContext:
    message: str
    session_id: int
    attachments: list[dict[str, Any]]
    history: list[dict[str, Any]]
    context: str
    intent: Any
    task: str
    llm: Any
    llm_message: str
    system: str
    knowledge: list[dict[str, Any]]
    enriched_knowledge: list[dict[str, Any]]
    citation_block: str
    shortcut: str | None = None

    @property
    def needs_citations(self) -> bool:
        return bool(self.knowledge and self.citation_block)
