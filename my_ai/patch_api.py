"""Run from project root: .venv\\Scripts\\python.exe patch_api.py"""
from pathlib import Path

path = Path("my_ai/api.py")
text = path.read_text(encoding="utf-8")
changed = False

# 1) database_import guard after classify in chat()
if "never hard-stop indicator/code file requests" not in text:
    old = "        intent=classify(msg)\n        # Learning and image generation have dedicated pages/endpoints."
    guard = '''        intent=classify(msg)
        # Guard: never hard-stop indicator/code file requests as database_import
        if intent.name == "database_import":
            _m = (
                "اندیکاتور", "indicator", "mql4", "mql5", "mq4", "mq5",
                "متاتریدر", "metatrader", ".mq4", ".mq5", "اکسپرت",
            )
            if any(t in low for t in _m) or (
                any(t in low for t in ("بساز", "بنویس", "دانلود", "ذخیره", "لینک", "download", "save"))
                and any(t in low for t in ("فایل", "file", "کد", "code", "اندیکاتور", "indicator", "mql"))
            ):
                from .domain.router import Intent as DomainIntent
                intent = DomainIntent(
                    name="coding",
                    confidence=float(getattr(intent, "confidence", 0.5) or 0.5),
                    requires_confirmation=False,
                    args=dict(getattr(intent, "args", {}) or {}),
                    intents=("coding",),
                )
        # Learning and image generation have dedicated pages/endpoints.'''
    if old not in text:
        raise SystemExit("classify guard site not found")
    text = text.replace(old, guard, 1)
    changed = True
    print("applied database_import guard")
else:
    print("database_import guard already present")

# 2) For indicator/MQL coding requests: use agent.chat (saves file) instead of build_project / generate_program only
marker = "        if code_intent:\n            language=requested or \"Python\"\n            if policy.build:"
replacement = '''        if code_intent:
            language=requested or "Python"
            _indi = any(t in low for t in (
                "اندیکاتور", "indicator", "mql4", "mql5", "mq4", "mq5",
                "متاتریدر", "metatrader", ".mq4", ".mq5", "اکسپرت",
            ))
            # Indicator/MQL source: never require application-build confirmation; use agent (file save path).
            if _indi:
                answer = agent.chat(msg, sid, attachments=attachments)
                user_message = fetch_all(
                    "SELECT id FROM conversations WHERE session_id=? AND role='user' ORDER BY id DESC LIMIT 1",
                    (sid,),
                )
                if attachments and user_message:
                    execute(
                        "UPDATE chat_attachments SET conversation_id=? WHERE session_id=? AND conversation_id IS NULL",
                        (user_message[0]["id"], sid),
                    )
                return {
                    "type": "code",
                    "answer": answer,
                    "session_id": sid,
                    "attachments": [
                        {
                            **item,
                            "download_url": "/files/download?path="
                            + __import__("urllib.parse", fromlist=["quote"]).quote(item["path"], safe=""),
                        }
                        for item in attachments
                    ],
                }
            if policy.build:'''
if "Indicator/MQL source: never require application-build" not in text:
    if marker not in text:
        raise SystemExit("code_intent build site not found")
    text = text.replace(marker, replacement, 1)
    changed = True
    print("applied indicator agent path")
else:
    print("indicator agent path already present")

if changed:
    path.write_text(text, encoding="utf-8")
    print("wrote", path.resolve())
else:
    print("no changes needed")
