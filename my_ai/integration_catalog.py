"""No-code catalogs for multimodal providers, execution profiles and integrations."""
from __future__ import annotations
from .control_plane import put_record, list_records, set_enabled, delete_record


def register_multimodal(kind,name,config,enabled=True): return put_record(f"multimodal.{kind}",name,config,enabled=enabled)
def list_multimodal(kind): return list_records(f"multimodal.{kind}")
def register_execution_profile(name,config,enabled=True): return put_record("execution.profiles",name,config,enabled=enabled)
def list_execution_profiles(): return list_records("execution.profiles")
def register_integration(name,config,enabled=True): return put_record("integrations.catalog",name,config,enabled=enabled)
def list_integrations(): return list_records("integrations.catalog")
def register_webhook(name,config,enabled=True): return put_record("integrations.webhooks",name,config,enabled=enabled)
def list_webhooks(): return list_records("integrations.webhooks")


def map_event_action(event: str, action: str, *, enabled=True):
    return put_record("integrations.events", event, {"event": event, "action": action}, enabled=enabled)

def list_event_actions(): return list_records("integrations.events")
