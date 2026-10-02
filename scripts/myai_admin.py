#!/usr/bin/env python3
"""Unified administrative CLI.

The CLI intentionally uses the same registries/control-plane as the GUI. It is
not a second configuration system.
"""
from __future__ import annotations
import argparse, json
from my_ai.control_plane import list_records, list_actions
from my_ai.provider_catalog import list_providers, list_models
from my_ai.settings_store import get_setting_registry, export_registered_settings
from my_ai.scheduler import scheduler_status
from my_ai.readiness import readiness
from my_ai.observability import get_metrics_snapshot


def out(v): print(json.dumps(v, ensure_ascii=False, indent=2, default=str))

def main():
    p=argparse.ArgumentParser(description="My-AI administration")
    s=p.add_subparsers(dest="cmd",required=True)
    s.add_parser("status"); s.add_parser("health"); s.add_parser("sessions")
    for n in ("memory","tools","policies","learning","repairs","rollback","diagnostics"):
        q=s.add_parser(n); q.add_argument("--namespace")
    s.add_parser("config")
    s.add_parser("actions")
    a=p.parse_args()
    if a.cmd=="status": out({"providers":list_providers(),"models":list_models(),"actions":list_actions(20)})
    elif a.cmd=="health": out(readiness())
    elif a.cmd=="config": out({"registry":get_setting_registry(),"values":export_registered_settings()})
    elif a.cmd=="actions": out(list_actions(100))
    elif a.cmd=="sessions": out(list_records("agent.session"))
    elif a.cmd=="memory": out(list_records(a.namespace or "memory.policy"))
    elif a.cmd=="tools": out(list_records(a.namespace or "tools.catalog"))
    elif a.cmd=="policies": out(list_records(a.namespace or "policies.registry"))
    elif a.cmd=="learning": out(list_records(a.namespace or "knowledge.registry"))
    elif a.cmd=="repairs": out(list_records(a.namespace or "self_repair.policy"))
    elif a.cmd=="rollback": out(list_records(a.namespace or "self_update.policy"))
    else: out({"control_plane":list_records(a.namespace),"actions":list_actions(100)})
if __name__=="__main__": main()
