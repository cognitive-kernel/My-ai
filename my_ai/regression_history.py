from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parent.parent
HISTORY=ROOT/"evals"/"history"


def save(result: dict[str,Any], *, git_ref: str="unknown", dataset_version: str="baseline-v1") -> Path:
    HISTORY.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload={"timestamp":datetime.now(timezone.utc).isoformat(),"git_ref":git_ref,"dataset_version":dataset_version,"result":result}
    path=HISTORY/f"{stamp}-{git_ref[:12]}.json"
    path.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return path


def load(limit: int=50) -> list[dict[str,Any]]:
    if not HISTORY.exists(): return []
    files=sorted(HISTORY.glob("*.json"),reverse=True)[:max(1,min(500,limit))]
    result=[]
    for path in files:
        try: result.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError,UnicodeDecodeError,json.JSONDecodeError): continue
    return result
