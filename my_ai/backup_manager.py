"""Configuration-driven database backup/restore primitives."""
from __future__ import annotations
import os, shutil, time
from pathlib import Path
from .db import DB_PATH


def backup(destination: str, *, overwrite=False) -> dict:
    src=Path(DB_PATH); dst=Path(destination)
    if not src.exists(): raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists() and not overwrite: raise FileExistsError(dst)
    shutil.copy2(src,dst)
    return {"path":str(dst),"size":dst.stat().st_size,"created_at":time.time()}


def restore(source: str, *, target=None) -> dict:
    src=Path(source); dst=Path(target or DB_PATH)
    if not src.exists(): raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True,exist_ok=True)
    tmp=dst.with_suffix(dst.suffix+".restore.tmp")
    shutil.copy2(src,tmp); os.replace(tmp,dst)
    return {"path":str(dst),"size":dst.stat().st_size,"restored_at":time.time()}
