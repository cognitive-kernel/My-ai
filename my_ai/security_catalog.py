"""Schema-driven security policy helpers."""
from __future__ import annotations
from typing import Any
from .control_plane import put_record, list_records


def define_role(name: str, capabilities: list[str], *, version="1", enabled=True):
    return put_record("security.roles",name,{"capabilities":capabilities,"version":version},enabled=enabled)


def define_capability(name: str, actions: list[str], *, resource="*", version="1"):
    return put_record("security.capabilities",name,{"actions":actions,"resource":resource,"version":version},enabled=True)


def set_permission(role: str, resource: str, actions: list[str], *, users=None):
    return put_record("security.approvals",f"{role}:{resource}",{"role":role,"resource":resource,"actions":actions,"users":users or []},enabled=True)


def set_network_policy(name, allowlist=None, denylist=None, *, default="deny"):
    return put_record("security.network",name,{"allowlist":allowlist or [],"denylist":denylist or [],"default":default},enabled=True)


def set_filesystem_policy(name, roots=None, read=True, write=False):
    return put_record("security.filesystem",name,{"roots":roots or [],"read":read,"write":write},enabled=True)


def set_subprocess_policy(name, commands=None, timeout=30):
    return put_record("security.subprocess",name,{"commands":commands or [],"timeout":timeout},enabled=True)


def set_export_policy(name, *, allow=True, require_approval=True, formats=None):
    return put_record("security.export", name, {"allow": bool(allow), "require_approval": bool(require_approval), "formats": formats or ["json"]}, enabled=True)


def set_versioning_policy(name, *, required=True, immutable_history=True, compatibility_check=True):
    return put_record("security.versioning", name, {"required": bool(required), "immutable_history": bool(immutable_history), "compatibility_check": bool(compatibility_check)}, enabled=True)


def list_security_policies():
    return {n:list_records(n) for n in ("security.roles","security.capabilities","security.approvals","security.network","security.filesystem","security.subprocess","security.export","security.versioning")}


def set_self_modification_policy(name, allowed_paths=None, require_approval=True, require_tests=True):
    return put_record("security.self_modification", name, {"allowed_paths": allowed_paths or [], "require_approval": bool(require_approval), "require_tests": bool(require_tests)}, enabled=True)
