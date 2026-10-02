#!/usr/bin/env python3
"""No-code control-plane CLI; every mutation maps to the same persistence used by GUI."""
from __future__ import annotations
import argparse, json
from my_ai.control_plane import (
    namespace_catalog, list_records, get_record, put_record, set_enabled,
    delete_record, start_action, update_action, get_action, list_actions,
)

def out(v): print(json.dumps(v, ensure_ascii=False, indent=2, default=str))

def main():
    p=argparse.ArgumentParser(description="My-AI unified control plane")
    s=p.add_subparsers(dest="cmd", required=True)
    for name in ("namespaces","list","get","put","enable","disable","delete","action-start","action-update","action-get","actions"):
        s.add_parser(name)
    p._subparsers._group_actions[0].choices["list"].add_argument("--namespace")
    p._subparsers._group_actions[0].choices["list"].add_argument("--include-disabled", action="store_true")
    for n in ("get","enable","disable","delete"):
        q=p._subparsers._group_actions[0].choices[n]; q.add_argument("namespace"); q.add_argument("name")
    q=p._subparsers._group_actions[0].choices["put"]; q.add_argument("namespace"); q.add_argument("name"); q.add_argument("--json", default="{}"); q.add_argument("--disabled", action="store_true")
    q=p._subparsers._group_actions[0].choices["action-start"]; q.add_argument("action"); q.add_argument("namespace"); q.add_argument("--target-id")
    q=p._subparsers._group_actions[0].choices["action-update"]; q.add_argument("id"); q.add_argument("status"); q.add_argument("--progress",type=float,default=0); q.add_argument("--json",default="{}"); q.add_argument("--error",default="")
    q=p._subparsers._group_actions[0].choices["action-get"]; q.add_argument("id")
    q=p._subparsers._group_actions[0].choices["actions"]; q.add_argument("--limit",type=int,default=100)
    a=p.parse_args()
    if a.cmd=="namespaces": out(namespace_catalog())
    elif a.cmd=="list": out(list_records(a.namespace, a.include_disabled))
    elif a.cmd=="get": out(get_record(a.namespace,a.name))
    elif a.cmd=="put": out(put_record(a.namespace,a.name,json.loads(a.json),enabled=not a.disabled))
    elif a.cmd in ("enable","disable"): out(set_enabled(a.namespace,a.name,a.cmd=="enable"))
    elif a.cmd=="delete": out({"deleted":delete_record(a.namespace,a.name)})
    elif a.cmd=="action-start": out(start_action(a.action,a.namespace,a.target_id))
    elif a.cmd=="action-update": out(update_action(a.id,status=a.status,progress=a.progress,result=json.loads(a.json),error=a.error))
    elif a.cmd=="action-get": out(get_action(a.id))
    else: out(list_actions(a.limit))
if __name__=="__main__": main()
