"""Compatibility facade for the layered domain router."""
from .domain.router import Intent, classify, router_tool_call, _parse_router_payload

__all__ = ["Intent", "classify", "router_tool_call", "_parse_router_payload"]
