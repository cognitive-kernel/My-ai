# Run from D:\Projects\MY-AI
Set-Location D:\Projects\MY-AI
@'
"""Public compatibility facade for the application-layer router."""
from .application.router import RouterService, build_router_service, classify
from .domain.router import Intent, ROUTER_TOOL_SCHEMA, router_tool_call, _parse_router_payload

__all__ = ["Intent", "ROUTER_TOOL_SCHEMA", "RouterService", "build_router_service", "classify", "router_tool_call", "_parse_router_payload"]
'@ | Set-Content -Path ".\my_ai\router.py" -Encoding utf8
Write-Host "my_ai\router.py facade restored"
Write-Host "ALLOWED_INTENTS in facade? $((Get-Content .\my_ai\router.py -Raw) -match 'ALLOWED_INTENTS')"
Write-Host "Has facade marker? $((Get-Content .\my_ai\router.py -Raw) -match 'Public compatibility facade')"
