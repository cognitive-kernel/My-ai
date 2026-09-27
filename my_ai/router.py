"""Compatibility facade for the layered domain router."""
from .domain.router import Intent, ROUTER_TOOL_SCHEMA, classify, router_tool_call, _parse_router_payload

__all__ = ["Intent", "ROUTER_TOOL_SCHEMA", "classify", "router_tool_call", "_parse_router_payload"]
