"""Compatibility facade for the semantic domain router.

All routing decisions are delegated to ``my_ai.domain.router`` so the runtime
does not maintain a second static trigger-word classifier.
"""

from .domain.router import (
    ACTION_VALUES, ALLOWED_INTENTS, HIGH_RISK, ROUTER_SCHEMA, ROUTER_TOOL_SCHEMA,
    Intent, _intent_from_payload, _parse_router_payload, classify, router_tool_call,
)

__all__ = ["ACTION_VALUES","ALLOWED_INTENTS","HIGH_RISK","ROUTER_SCHEMA","ROUTER_TOOL_SCHEMA","Intent","_intent_from_payload","_parse_router_payload","classify","router_tool_call"]
