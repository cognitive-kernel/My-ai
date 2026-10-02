"""Versioned prompt, policy and tool registries used by the control plane."""
from __future__ import annotations
from typing import Any
from .control_plane import put_record, list_records, get_record


def publish_prompt(name: str, text: str, *, task: str="default", version: str="1", enabled: bool=False, metadata=None):
    return put_record("prompts.registry", name, {"text":text,"task":task,"version":version,"metadata":metadata or {}}, enabled=enabled)


def activate_prompt(name: str): return put_record("prompts.registry",name,(get_record("prompts.registry",name) or {}).get("payload",{}),enabled=True)


def publish_policy(name: str, policy: dict[str,Any], *, version: str="1", enabled: bool=False):
    payload=dict(policy); payload["version"]=version
    return put_record("policies.registry",name,payload,enabled=enabled)


def register_tool(name: str, description: str, input_schema: dict[str,Any], output_schema: dict[str,Any], *,
                  permissions=None, timeout=30, retries=2, tasks=None, version="1", enabled=True):
    return put_record("tools.catalog",name,{
        "description":description,"input_schema":input_schema,"output_schema":output_schema,
        "permissions":permissions or [],"timeout":timeout,"retries":retries,"tasks":tasks or [],"version":version
    },enabled=enabled)


def list_tools(): return list_records("tools.catalog")
