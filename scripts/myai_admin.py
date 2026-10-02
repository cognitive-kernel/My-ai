#!/usr/bin/env python3
"""Unified administrative CLI backed by the same no-code control plane as the GUI."""
from __future__ import annotations
import argparse, json
from my_ai.control_plane import (
    list_records, get_record, put_record, set_enabled, delete_record,
    start_action, update_action, list_actions, namespace_catalog,
)
from my_ai.provider_catalog import (
    list_providers, list_models, upsert_provider, delete_provider, delete_model,
    upsert_model, delete_model, add_provider_key, list_provider_keys, rotate_provider_key,
)
from my_ai.settings_store import get_setting_registry, export_registered_settings, list_setting_history, set_setting, reset_setting
from my_ai.readiness import build_readiness
from my_ai.learning_catalog import list_sources, add_source, review_source
from my_ai.config_profiles import save_profile, active_profile, load_profile
from my_ai.backup_manager import backup, restore
from my_ai.no_code_catalog import inventory

def out(v): print(json.dumps(v, ensure_ascii=False, indent=2, default=str))

def main():
    p=argparse.ArgumentParser(description="My-AI administration")
    s=p.add_subparsers(dest="cmd", required=True)

    s.add_parser("status"); s.add_parser("health"); s.add_parser("config"); s.add_parser("capabilities")
    s.add_parser("actions"); s.add_parser("namespaces"); s.add_parser("config-history"); s.add_parser("profile-active")
    q=s.add_parser("profile-save"); q.add_argument("name"); q.add_argument("settings"); q.add_argument("--activate",action="store_true")
    q=s.add_parser("profile-load"); q.add_argument("name")
    q=s.add_parser("backup"); q.add_argument("path"); q.add_argument("--overwrite",action="store_true")
    q=s.add_parser("restore"); q.add_argument("path"); q.add_argument("--target")
    s.add_parser("learning-sources")
    q=s.add_parser("learning-source-add"); q.add_argument("url"); q.add_argument("--type",default="custom"); q.add_argument("--product",default=""); q.add_argument("--version",default=""); q.add_argument("--priority",type=int,default=100)
    q=s.add_parser("learning-source-review"); q.add_argument("source_id",type=int); q.add_argument("status",choices=["approved","rejected","pending"])
    q=s.add_parser("config-set"); q.add_argument("key"); q.add_argument("value")
    q=s.add_parser("config-reset"); q.add_argument("key")
    q=s.add_parser("config-export"); q.add_argument("path")
    q=s.add_parser("config-import"); q.add_argument("path")
    for n in ("sessions","memory","tools","policies","learning","repairs","rollback","diagnostics"):
        q=s.add_parser(n); q.add_argument("--namespace")

    q=s.add_parser("record-get"); q.add_argument("namespace"); q.add_argument("name")
    q=s.add_parser("record-put"); q.add_argument("namespace"); q.add_argument("name"); q.add_argument("payload"); q.add_argument("--disabled",action="store_true")
    q=s.add_parser("record-enable"); q.add_argument("namespace"); q.add_argument("name")
    q=s.add_parser("record-disable"); q.add_argument("namespace"); q.add_argument("name")
    q=s.add_parser("record-delete"); q.add_argument("namespace"); q.add_argument("name")

    q=s.add_parser("action-start"); q.add_argument("action"); q.add_argument("namespace"); q.add_argument("--target-id")
    q=s.add_parser("action-update"); q.add_argument("action_id"); q.add_argument("status"); q.add_argument("--progress",type=float,default=0); q.add_argument("--result",default="{}"); q.add_argument("--error",default="")

    q=s.add_parser("provider-list")
    q=s.add_parser("provider-delete"); q.add_argument("provider_id",type=int)
    q=s.add_parser("provider-key-list"); q.add_argument("provider_id",type=int)
    q=s.add_parser("provider-key-add"); q.add_argument("provider_id",type=int); q.add_argument("key_name"); q.add_argument("secret"); q.add_argument("--priority",type=int,default=100)
    q=s.add_parser("provider-key-rotate"); q.add_argument("provider_id",type=int)
    q=s.add_parser("provider-upsert"); q.add_argument("name"); q.add_argument("protocol"); q.add_argument("endpoint"); q.add_argument("--provider-id",type=int); q.add_argument("--auth-type",default="none"); q.add_argument("--secret",default=""); q.add_argument("--version",default=""); q.add_argument("--timeout",type=float,default=30); q.add_argument("--disabled",action="store_true")
    q=s.add_parser("model-upsert"); q.add_argument("provider_id",type=int); q.add_argument("model_id"); q.add_argument("--tasks",default=""); q.add_argument("--context",type=int); q.add_argument("--priority",type=int,default=100); q.add_argument("--version",default=""); q.add_argument("--disabled",action="store_true")
    q=s.add_parser("model-delete"); q.add_argument("provider_id",type=int); q.add_argument("model_id")

    a=p.parse_args()
    if a.cmd=="status": out({"providers":list_providers(),"models":list_models(),"actions":list_actions(20)})
    elif a.cmd=="health": out(build_readiness())
    elif a.cmd=="capabilities": out(inventory())
    elif a.cmd=="config": out({"registry":get_setting_registry(),"values":export_registered_settings()})
    elif a.cmd=="actions": out(list_actions(100))
    elif a.cmd=="namespaces": out(namespace_catalog())
    elif a.cmd=="config-history": out(list_setting_history())
    elif a.cmd=="profile-active": out({"name":active_profile()})
    elif a.cmd=="profile-save": out(save_profile(a.name,json.loads(a.settings),activate=a.activate))
    elif a.cmd=="profile-load": out(load_profile(a.name))
    elif a.cmd=="backup": out({"path":backup(a.path,overwrite=a.overwrite)})
    elif a.cmd=="restore": out({"path":restore(a.path,target=a.target)})
    elif a.cmd=="learning-sources": out(list_sources())
    elif a.cmd=="learning-source-add": out(add_source(a.url,source_type=a.type,product=a.product,version=a.version,priority=a.priority))
    elif a.cmd=="learning-source-review": out(review_source(a.source_id,a.status))
    elif a.cmd=="config-set":
        meta=get_setting_registry().get(a.key)
        if not meta: raise SystemExit(f"Unknown setting: {a.key}")
        raw=a.value
        if meta.get("type")=="int": raw=int(raw)
        elif meta.get("type")=="float": raw=float(raw)
        set_setting(a.key,raw,secret=bool(meta.get("secret"))); out({"key":a.key,"saved":True})
    elif a.cmd=="config-reset": out({"key":a.key,"value":reset_setting(a.key),"reset":True})
    elif a.cmd=="config-export":
        with open(a.path,"w",encoding="utf-8") as f: json.dump(export_registered_settings(),f,ensure_ascii=False,indent=2); out({"path":a.path,"exported":True})
    elif a.cmd=="config-import":
        with open(a.path,encoding="utf-8") as f: values=json.load(f)
        if not isinstance(values,dict): raise SystemExit("config import must be a JSON object")
        for key,value in values.items():
            meta=get_setting_registry().get(key)
            if meta: set_setting(key,value,secret=bool(meta.get("secret")))
        out({"path":a.path,"imported":len(values)})
    elif a.cmd=="sessions": out(list_records("agent.session"))
    elif a.cmd=="memory": out(list_records(a.namespace or "memory.policy"))
    elif a.cmd=="tools": out(list_records(a.namespace or "tools.catalog"))
    elif a.cmd=="policies": out(list_records(a.namespace or "policies.registry"))
    elif a.cmd=="learning": out(list_records(a.namespace or "knowledge.registry"))
    elif a.cmd=="repairs": out(list_records(a.namespace or "self_repair.policy"))
    elif a.cmd=="rollback": out(list_records(a.namespace or "self_update.policy"))
    elif a.cmd=="diagnostics": out({"control_plane":list_records(a.namespace),"actions":list_actions(100)})
    elif a.cmd=="record-get": out(get_record(a.namespace,a.name))
    elif a.cmd=="record-put":
        payload=json.loads(a.payload); out(put_record(a.namespace,a.name,payload,enabled=not a.disabled))
    elif a.cmd in ("record-enable","record-disable"):
        out(set_enabled(a.namespace,a.name,a.cmd=="record-enable"))
    elif a.cmd=="record-delete": out({"deleted":delete_record(a.namespace,a.name)})
    elif a.cmd=="action-start": out(start_action(a.action,a.namespace,a.target_id))
    elif a.cmd=="action-update": out(update_action(a.action_id,status=a.status,progress=a.progress,result=json.loads(a.result),error=a.error))
    elif a.cmd=="provider-list": out({"providers":list_providers(),"models":list_models()})
    elif a.cmd=="provider-delete": delete_provider(a.provider_id); out({"deleted":a.provider_id})
    elif a.cmd=="provider-key-list": out(list_provider_keys(a.provider_id))
    elif a.cmd=="provider-key-add": out(add_provider_key(a.provider_id,a.key_name,a.secret,priority=a.priority))
    elif a.cmd=="provider-key-rotate": out(rotate_provider_key(a.provider_id))
    elif a.cmd=="provider-upsert":
        out(upsert_provider(name=a.name,protocol=a.protocol,endpoint=a.endpoint,auth_type=a.auth_type,secret=a.secret,version=a.version,timeout_seconds=a.timeout,enabled=not a.disabled,provider_id=a.provider_id))
    elif a.cmd=="model-upsert":
        out(upsert_model(provider_id=a.provider_id,model_id=a.model_id,tasks=[x.strip() for x in a.tasks.split(",") if x.strip()],context_length=a.context,priority=a.priority,version=a.version,enabled=not a.disabled))
    elif a.cmd=="model-delete": delete_model(a.provider_id,a.model_id); out({"deleted":{"provider_id":a.provider_id,"model_id":a.model_id}})

if __name__=="__main__":
    main()
