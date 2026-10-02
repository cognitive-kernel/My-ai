"""Safe plugin/provider installation catalog; actual installation remains policy-gated."""
from __future__ import annotations
from .control_plane import put_record, get_record


def propose_plugin(name, source, version, capabilities, checksum=""):
    return put_record("plugins.registry",name,{"source":source,"version":version,"capabilities":capabilities,"checksum":checksum,"state":"candidate"},enabled=False)


def approve_plugin(name):
    item=get_record("plugins.registry",name)
    if not item: raise KeyError(name)
    payload=dict(item["payload"]); payload["state"]="approved"
    return put_record("plugins.registry",name,payload,enabled=True)


def reject_plugin(name,reason=""):
    item=get_record("plugins.registry",name)
    if not item: raise KeyError(name)
    payload=dict(item["payload"]); payload["state"]="rejected"; payload["reason"]=reason
    return put_record("plugins.registry",name,payload,enabled=False)
