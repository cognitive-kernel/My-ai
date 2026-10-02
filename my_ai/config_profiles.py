"""Configuration profile management backed by the unified control plane."""
from __future__ import annotations
from .control_plane import put_record, get_record


def save_profile(name: str, settings: dict, *, activate=False):
    item=put_record("config.profiles",name,{"settings":settings},enabled=True)
    if activate: put_record("config.profiles","__active__",{"name":name},enabled=True)
    return item


def active_profile():
    item=get_record("config.profiles","__active__")
    return item.get("payload",{}).get("name") if item else None


def load_profile(name):
    item=get_record("config.profiles",name)
    if not item: raise KeyError(name)
    return item.get("payload",{}).get("settings",{})
