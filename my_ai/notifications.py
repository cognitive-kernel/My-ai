from __future__ import annotations

import json
import os
import urllib.request
from .config import settings

def notify(event: str, payload: dict[str, object]) -> bool:
    if settings.offline_strict:
        return False
    url = os.getenv("MYAI_NOTIFICATION_WEBHOOK", "").strip()
    if not url:
        return False
    body = json.dumps({"event": event, "payload": payload}, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return 200 <= int(response.status) < 300
    except Exception:
        return False
