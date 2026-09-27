"""Compatibility facade for the layered domain router.

New code should import from my_ai.domain.router; this module remains stable for
existing integrations and tests.
"""
from .domain.router import *
from .domain.router import Intent, classify, router_tool_call, _parse_router_payload
