"""Run from project root: .venv\\Scripts\\python.exe patch_api.py"""
from pathlib import Path

path = Path("my_ai/api.py")
text = path.read_text(encoding="utf-8")
changed = False

# 1) database_import guard
if "never hard-stop indicator/code file requests" not in text:
    old = "        intent=classify(msg)\n        # Learning and image generation have dedicated pages/endpoints."
    guard = (
        "        intent=classify(msg)\n"
        "        # Guard: never hard-stop indicator/code file requests as database_import\n"
        "        if intent.name == \"database_import\":\n"
        "            _m = (\n"
        "                \"اندیکاتور\", \"indicator\", \"mql4\", \"mql5\", \"mq4\", \"mq5\",\n"
        "                \"متاتریدر\", \"metatrader\", \".mq4\", \".mq5\", \"اکسپرت\",\n"
        "            )\n"
        "            if any(t in low for t in _m) or (\n"
        "                any(t in low for t in (\"بساز\", \"بنویس\", \"دانلود\", \"ذخیره\", \"لینک\", \"download\", \"save\"))\n"
        "                and any(t in low for t in (\"فایل\", \"file\", \"کد\", \"code\", \"اندیکاتور\", \"indicator\", \"mql\"))\n"
        "            ):\n"
        "                from .domain.router import Intent as DomainIntent\n"
        "                intent = DomainIntent(\n"
        "                    name=\"coding\",\n"
        "                    confidence=float(getattr(intent, \"confidence\", 0.5) or 0.5),\n"
        "                    requires_confirmation=False,\n"
        "                    args=dict(getattr(intent, \"args\", {}) or {}),\n"
        "                    intents=(\"coding\",),\n"
        "                )\n"
        "        # Learning and image generation have dedicated pages/endpoints."
    )
    if old not in text:
        raise SystemExit("classify guard site not found")
    text = text.replace(old, guard, 1)
    changed = True
    print("applied database_import guard")
else:
    print("database_import guard already present")

# 2) Indicator -> agent.chat
marker = "        if code_intent:\n            language=requested or \"Python\"\n            if policy.build:"
replacement = (
    "        if code_intent:\n"
    "            language=requested or \"Python\"\n"
    "            _indi = any(t in low for t in (\n"
    "                \"اندیکاتور\", \"indicator\", \"mql4\", \"mql5\", \"mq4\", \"mq5\",\n"
    "                \"متاتریدر\", \"metatrader\", \".mq4\", \".mq5\", \"اکسپرت\",\n"
    "            ))\n"
    "            if _indi:\n"
    "                language = \"MQL4\"\n"
    "            # Indicator/MQL source: never require application-build confirmation; use agent (file save path).\n"
    "            if _indi:\n"
    "                answer = agent.chat(msg, sid, attachments=attachments)\n"
    "                user_message = fetch_all(\n"
    "                    \"SELECT id FROM conversations WHERE session_id=? AND role='user' ORDER BY id DESC LIMIT 1\",\n"
    "                    (sid,),\n"
    "                )\n"
    "                if attachments and user_message:\n"
    "                    execute(\n"
    "                        \"UPDATE chat_attachments SET conversation_id=? WHERE session_id=? AND conversation_id IS NULL\",\n"
    "                        (user_message[0][\"id\"], sid),\n"
    "                    )\n"
    "                return {\n"
    "                    \"type\": \"code\",\n"
    "                    \"answer\": answer,\n"
    "                    \"session_id\": sid,\n"
    "                    \"attachments\": [\n"
    "                        {\n"
    "                            **item,\n"
    "                            \"download_url\": \"/files/download?path=\"\n"
    "                            + __import__(\"urllib.parse\", fromlist=[\"quote\"]).quote(item[\"path\"], safe=\"\"),\n"
    "                        }\n"
    "                        for item in attachments\n"
    "                    ],\n"
    "                }\n"
    "            if policy.build:"
)
if "Indicator/MQL source: never require application-build" not in text:
    if marker not in text:
        raise SystemExit("code_intent build site not found")
    text = text.replace(marker, replacement, 1)
    changed = True
    print("applied indicator agent path")
else:
    print("indicator agent path already present")

# 3) Force MQL4 language for generate_program fallback
needle = "            generated_data=learner.generate_program(msg,language)"
if needle in text and 'language = "MQL4"\n            generated_data=learner.generate_program' not in text:
    force = (
        "            if any(t in low for t in (\"اندیکاتور\", \"indicator\", \"mql4\", \"mql5\", \"mq4\", \"mq5\", \"متاتریدر\", \"metatrader\")):\n"
        "                language = \"MQL4\"\n"
        "            generated_data=learner.generate_program(msg,language)"
    )
    text = text.replace(needle, force, 1)
    changed = True
    print("applied MQL4 language force")
else:
    print("MQL4 language force skipped or present")

# 4) Expand answer with file paths
if "فایل(ها) ذخیره شد" not in text:
    old_a = '            generated_answer="Generated program:"'
    new_a = (
        "            _code = str((generated_data or {}).get(\"code\") or \"\")\n"
        "            _files = (generated_data or {}).get(\"files\") or []\n"
        "            _pp = str((generated_data or {}).get(\"project_path\") or \"\")\n"
        "            _files_txt = (\"\\n\".join(\"- \" + str(f) for f in _files)\n"
        "                         if _files else (\"- projects/\" + str((generated_data or {}).get(\"project_name\") or \"\") + \"/\"))\n"
        "            generated_answer = (\n"
        "                \"Generated program (\" + str((generated_data or {}).get(\"language\") or language) + \"):\\n\\n\"\n"
        "                + _code\n"
        "                + \"\\n\\n---\\nفایل(ها) ذخیره شد:\\n\"\n"
        "                + _files_txt\n"
        "                + ((\"\\nمسیر نسبی پروژه: \" + _pp) if _pp else \"\")\n"
        "                + \"\\n\\nنصب MetaTrader 4: فایل .mq4 را در MQL4/Experts یا MQL4/Indicators کپی و Compile کنید. \"\n"
        "                + \"اندیکاتور OrderSend ندارد؛ برای معامله از Expert Advisor استفاده کنید.\"\n"
        "            )"
    )
    if old_a not in text:
        raise SystemExit("generated_answer assignment not found")
    text = text.replace(old_a, new_a, 1)
    changed = True
    print("applied answer with file paths")
else:
    print("answer path expansion already present")

if changed:
    path.write_text(text, encoding="utf-8")
    print("wrote", path.resolve())
else:
    print("no changes needed")
