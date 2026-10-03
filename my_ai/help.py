from __future__ import annotations

import json
from html import escape
from pathlib import Path

from .access_policy import assert_mutation_allowed
from .db import execute, fetch_all

MASTER_GUIDE = Path(__file__).resolve().parent.parent / "docs" / "MY_AI_MASTER_GUIDE.md"

COMPONENT_TITLES = {
    "chat": "چت و گفتگو",
    "learning": "یادگیری",
    "coding": "برنامه‌نویسی",
    "security": "امنیت",
    "git": "Git / GitHub",
    "memory": "حافظه",
    "scheduler": "Scheduler",
    "voice": "صدا",
    "api": "API",
    "docker": "Docker",
    "network-policy": "شبکه و سیاست آفلاین",
    "self-development": "خودپایش و توسعه",
    "metatrader": "MetaTrader 4/5",
    "settings": "تنظیمات",
}

def _guide_text() -> str:
    if not MASTER_GUIDE.exists():
        return "راهنمای اصلی پروژه در مسیر docs/MY_AI_MASTER_GUIDE.md یافت نشد."
    return MASTER_GUIDE.read_text(encoding="utf-8")

def _guide_sections() -> list[tuple[str, str]]:
    lines = _guide_text().splitlines()
    sections = []
    title = ""
    body = []
    for line in lines:
        if line.startswith("## "):
            if title:
                sections.append((title, "\n".join(body).strip()))
            title, body = line[3:].strip(), [line]
        elif title:
            body.append(line)
    if title:
        sections.append((title, "\n".join(body).strip()))
    return sections

def local_help(component: str | None) -> str:
    key = (component or "chat").lower().strip()
    if key not in COMPONENT_TITLES:
        return _guide_text()
    aliases = {
        "chat": ("dynamic", "agent", "chat"),
        "learning": ("learning", "یادگیری"),
        "coding": ("coding", "software", "برنامه"),
        "security": ("security", "امنیت"),
        "git": ("git", "github"),
        "memory": ("memory", "حافظه"),
        "scheduler": ("scheduler", "event"),
        "voice": ("voice", "صدا"),
        "api": ("api",),
        "docker": ("docker",),
        "network-policy": ("security", "network", "offline"),
        "self-development": ("self-repair", "self-development", "self-update"),
        "metatrader": ("metatrader", "MetaTrader"),
        "settings": ("settings", "تنظیمات"),
    }
    needles = aliases.get(key, (COMPONENT_TITLES[key],))
    selected = []
    for section_title, body in _guide_sections():
        text = (section_title + "\n" + body).lower()
        if any(needle.lower() in text for needle in needles):
            selected.append(body)
    return "\n\n".join(selected) if selected else _guide_text()

def local_help_html(component: str | None) -> str:
    out = []
    for line in local_help(component).splitlines():
        if line.startswith("# "):
            out.append("<h2>" + escape(line[2:]) + "</h2>")
        elif line.startswith("## "):
            out.append("<h3>" + escape(line[3:]) + "</h3>")
        elif line.startswith("- "):
            out.append("<li>" + escape(line[2:]) + "</li>")
        elif line.strip():
            out.append("<p>" + escape(line) + "</p>")
    return "".join(out)

def apply_help_update(component: str, proposal: str) -> bool:
    assert_mutation_allowed("help update")
    key = (component or "").lower().strip()
    if key not in COMPONENT_TITLES or not proposal.strip():
        return False
    # Runtime help must never rewrite the master guide. Approved proposals are
    # stored by the API and enter the source tree only through reviewed Git changes.
    return True

def page() -> str:
    updates = fetch_all(
        "SELECT * FROM help_updates WHERE status='approved' "
        "ORDER BY id DESC LIMIT 30"
    )
    approved = "".join(
        "<section class='card'><h2>پیشنهاد تأییدشده: "
        + escape(u["component"])
        + "</h2><pre>"
        + escape(u["proposed_update"] or u["answer"])
        + "</pre><p><small>منابع: "
        + escape(u["sources"] or "")
        + "</small></p></section>"
        for u in updates
    )
    guide = escape(local_help(None))
    return """<!doctype html>
<html lang="fa" dir="rtl"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>My-AI — راهنمای اصلی</title>
<style>
body{font-family:Tahoma,system-ui;line-height:1.9;margin:0;background:#f3f4f6;color:#17202a}
main{max-width:1100px;margin:auto;padding:24px}
.card{background:#fff;padding:22px;border-radius:14px;margin:14px 0;border:1px solid #e5e7eb}
.hero{background:#111827;color:#fff;padding:24px;border-radius:18px;margin-bottom:16px}
pre{direction:ltr;text-align:left;white-space:pre-wrap;overflow:auto}
</style></head><body><main>
<section class="hero"><h1>My-AI — راهنمای اصلی</h1>
<p>این صفحه مستقیماً از docs/MY_AI_MASTER_GUIDE.md تغذیه می‌شود.</p></section>
<section class="card"><h2>منبع واحد حقیقت</h2>
<p>راهنماهای قدیمی مستقل منبع اجرایی نیستند. تغییرات مستنداتی باید از مسیر Git و بازبینی مهندسی وارد فایل اصلی شوند.</p></section>
<section class="card"><h2>راهنمای پروژه</h2><pre>""" + guide + """</pre></section>""" + approved + """</main></body></html>"""

def ask_help(question, component, llm, web):
    domains = {
        "git": ["docs.github.com", "github.com"],
        "security": ["owasp.org", "portswigger.net", "nmap.org"],
        "python": ["docs.python.org"],
        "php": ["php.net", "getcomposer.org"],
        "javascript": ["developer.mozilla.org"],
        "docker": ["docs.docker.com"],
        "api": ["fastapi.tiangolo.com"],
        "metatrader": ["mql5.com", "docs.mql4.com"],
    }.get((component or "").lower())

    results = web.search(question, domains=domains, limit=6)
    fetched = []
    for item in results[:4]:
        try:
            title, body = web.fetch(item["url"])
            fetched.append({"title": title, "url": item["url"], "content": body[:12000]})
        except Exception:
            fetched.append(item)

    current_help = local_help(component)
    answer = llm.chat(
        "Answer the user's question about using this My-AI feature. Be practical and concise. "
        "Use the master guide as the authoritative local source. Distinguish external instructions "
        "from the project's implementation and do not invent steps.\nQUESTION: " + question
        + "\nCOMPONENT: " + component
        + "\nMASTER GUIDE VIEW:\n" + current_help
        + "\nEXTERNAL SOURCES:\n" + json.dumps(fetched, ensure_ascii=False),
        system="You are the My-AI product help assistant. Cite source URLs in plain text.",
    )
    proposal = llm.chat(
        "Compare the master guide view with current documentation. Return a concise proposed "
        "documentation change only if a real change is needed; otherwise return NO_CHANGE. "
        "Never modify the guide yourself. The proposal requires a reviewed Git change.\nQUESTION: "
        + question + "\nCURRENT MASTER GUIDE VIEW:\n" + current_help
        + "\nCURRENT SOURCES:\n" + json.dumps(fetched, ensure_ascii=False),
        system="Return either NO_CHANGE or a short proposed change.",
    )
    rid = execute(
        "INSERT INTO help_updates(component,question,status,answer,sources,proposed_update) VALUES(?,?,?,?,?,?)",
        (component, question, "pending", answer,
         json.dumps([x.get("url") for x in fetched], ensure_ascii=False), proposal),
    )
    return {
        "id": rid, "component": component, "answer": answer,
        "sources": [x.get("url") for x in fetched],
        "proposed_update": proposal, "status": "pending",
    }
