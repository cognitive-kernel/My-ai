from __future__ import annotations

from ..core.protocols import StructuredRouter
from ..domain.router import Intent, classify as domain_classify
from ..infra.router_llm import create_structured_router
from ..config import settings


class RouterService:
    """Application service that composes the domain router with an injected model adapter."""

    def __init__(self, classifier: StructuredRouter | None = None) -> None:
        self._classifier = classifier

    def classify(self, text: str, context: str | None = None) -> Intent:
        if self._classifier is None and not getattr(settings, "router_llm_enabled", True):
            return domain_classify(text, context, None)
        classifier = self._classifier or create_structured_router()
        return domain_classify(text, context, classifier)


_default_service = RouterService()


def classify(text: str, context: str | None = None) -> Intent:
    return _default_service.classify(text, context)


class _SafeNoopRouter:
    def structured_chat_json(self, message, schema, system=None):
        return {
            "primary": "chat", "intents": ["chat"], "action": "answer", "confidence": 0.0,
            "language": None, "topic": None, "goal": None, "project_path": None, "urls": [],
        }


def build_router_service(classifier: StructuredRouter | None = None) -> RouterService:
    """Explicitly injected service; None means deterministic safe-chat test adapter."""
    return RouterService(_SafeNoopRouter() if classifier is None else classifier)
