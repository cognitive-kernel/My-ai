"""Public compatibility facade for the application-layer router."""
from .application.router import RouterService, build_router_service, classify
from .domain.router import Intent, ROUTER_TOOL_SCHEMA, router_tool_call, _parse_router_payload

__all__ = ["Intent", "ROUTER_TOOL_SCHEMA", "RouterService", "build_router_service", "classify", "router_tool_call", "_parse_router_payload"]
