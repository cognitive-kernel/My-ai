from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata
import json
from typing import Any, Iterable

from ..config import settings


@dataclass(frozen=True)
class Intent:
    name: str
    confidence: float
    requires_confirmation: bool = False
    args: dict[str, Any] = field(default_factory=dict)
    intents: tuple[str, ...] = ()


HIGH_RISK = {"pentest_external", "git_write", "self_update", "database_import", "code_execution", "self_repair"}

ROUTER_TOOL_SCHEMA = {
    "name": "route_request",
    "description": "Return a structured intent and tool arguments. Never authorize execution by itself.",
    "parameters": {
        "type": "object",
        "additionalProperties": False,
        "required": ["primary", "intents", "confidence", "language", "topic", "goal"],
        "properties": {
            "primary": {"type": "string"},
            "intents": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "language": {"type": ["string", "null"]},
            "topic": {"type": ["string", "null"]},
            "goal": {"type": ["string", "null"]},
        },
    },
}


def router_tool_call(intent: Intent) -> dict[str, Any]:
    """Serialize routing separately from authorization/execution."""
    return {
        "name": ROUTER_TOOL_SCHEMA["name"],
        "arguments": {
            "primary": intent.name,
            "intents": list(intent.intents or (intent.name,)),
            "confidence": float(intent.confidence),
            "language": intent.args.get("language"),
            "topic": intent.args.get("topic"),
            "goal": intent.args.get("goal"),
        },
    }


def _parse_router_payload(raw: str) -> dict[str, Any]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Router output must be a JSON object.")
    required = ("primary", "intents", "confidence", "language", "topic", "goal")
    if any(key not in data for key in required):
        raise ValueError("Router output is missing required fields.")
    return data

_INTENT_PATTERNS: dict[str, tuple[tuple[str, float], ...]] = {
    "self_update": (
        ("self update", 1.8), ("self-update", 1.8), ("آپدیت خودت", 2.0),
        ("به روزرسانی خودت", 2.0), ("بروزرسانی خودت", 2.0),
        ("خودت رو آپدیت", 2.0), ("خودت را آپدیت", 2.0),
        ("آپدیت خودت رو", 2.0), ("خودت را به روز کن", 2.0),
    ),
    "git_write": (
        ("git write", 1.8), ("github بنویس", 2.0), ("در گیت تغییر بده", 2.0),
        ("روی گیت تغییر بده", 2.0), ("در گیتهاب تغییر بده", 2.0),
        ("فایل را در گیت", 1.8), ("فایل رو در گیت", 1.8),
        ("کامیت کن", 1.8), ("commit کن", 1.8), ("commit", 1.4), ("push کن", 1.7),
    ),
    "pentest_external": (
        ("پن تست", 1.8), ("پنتست", 1.8), ("pentest", 1.8),
        ("تست نفوذ", 1.8), ("آسیب پذیری آدرس", 1.6), ("اسکن امنیتی آدرس", 1.5),
    ),
    "self_repair": (
        ("خودت را تعمیر کن", 1.9), ("خودتو تعمیر کن", 1.9), ("خودت رو تعمیر کن", 1.9),
        ("تعمیر خودت", 1.8), ("باگ خودت را درست کن", 1.9), ("باگ خودتو درست کن", 1.9),
        ("خودت را درست کن", 1.9), ("self repair", 1.8), ("self-repair", 1.8),
        ("repair yourself", 1.8), ("fix yourself", 1.8), ("fix your own bugs", 1.8),
    ),
    "learning": (
        ("یاد بگیر", 1.5), ("یادگیری", 1.3), ("یاد بده", 1.4),
        ("یاد بگیرش", 1.5), ("شروع به یادگیری", 1.5), ("ادامه یادگیری", 1.5),
        ("مطالعه", 1.2), ("study this", 1.4), ("learn this", 1.4),
        ("آموزش بده", 1.5), ("آموزش", 1.1), ("درس", 1.0),
        ("مطالعه کن", 1.4), ("یاد بگیرم", 1.5), ("learn", 1.4),
        ("study", 1.3), ("teach me", 1.5),
    ),
    "code_execution": (
        ("کد را اجرا کن", 1.8), ("کد رو اجرا کن", 1.8),
        ("کد را ران کن", 1.8), ("کد رو ران کن", 1.8),
        ("اجراش کن", 1.8), ("رانش کن", 1.8), ("اجرا کن", 1.4),
        ("ران کن", 1.4), ("run this code", 1.8), ("run it", 1.6),
        ("execute this", 1.7), ("execute it", 1.6),
    ),
    "security_scan": (
        ("اسکن امنیتی", 1.7), ("بررسی امنیتی", 1.6), ("security scan", 1.7),
        ("اسکن کد", 1.6), ("بررسی آسیب پذیری کد", 1.7), ("sast", 1.6),
        ("security assessment", 1.6),
    ),
    "help": (
        ("راهنما", 1.3), ("کمک", 1.2), ("help", 1.3), ("help me", 1.4),
        ("چطور کار میکند", 1.3), ("چطور کار می کنه", 1.3),
        ("راهنمایی کن", 1.3),
    ),
    "file_analysis": (
        ("فایل را تحلیل کن", 1.6), ("فایل رو تحلیل کن", 1.6),
        ("فایل را بررسی کن", 1.5), ("فایل رو بررسی کن", 1.5),
        ("فایل را بخوان و تحلیل کن", 1.7), ("analyze this file", 1.7),
        ("inspect this file", 1.6),
    ),
    "coding": (
        ("کد بنویس", 1.6), ("کد تولید کن", 1.6), ("کدنویسی کن", 1.5),
        ("برنامه بنویس", 1.6), ("یک برنامه بساز", 1.5),
        ("یه برنامه بساز", 1.5), ("یک پروژه بساز", 1.6), ("یه پروژه بساز", 1.6),
        ("پروژه بساز", 1.5), ("پروژه را در", 1.6), ("پروژه در", 1.5), ("api بساز", 1.6), ("ای پی آی بساز", 1.6),
        ("write code", 1.5), ("generate code", 1.5), ("build", 1.2), ("implement", 1.3),
        ("create code", 1.5),
        ("create a project", 1.5), ("build a project", 1.5),
    ),
}

_LANGUAGE_ALIASES = {
    "python": ("python", "پایتون"),
    "javascript": ("javascript", "js", "جاوااسکریپت", "جاوا اسکریپت"),
    "typescript": ("typescript", "ts", "تایپ اسکریپت"),
    "rust": ("rust", "راست"), "c": ("زبان c", "c language", "سی"),
    "php": ("php", "پی اچ پی"), "sql": ("sql", "اس کیو ال"),
    "mysql": ("mysql", "مای اس کیو ال"), "sqlite": ("sqlite", "اس کیو لایت"),
    "android": ("android", "اندروید"), "ios": ("ios", "آی او اس"),
    "cisco": ("cisco", "سیسکو", "ccna", "cisco networking", "شبکه سیسکو"),
}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", str(text)).casefold()
    text = text.replace("\u200c", " ").replace("\u200d", " ")
    text = text.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    text = re.sub(r"[\u064b-\u065f\u0670]", "", text)
    text = re.sub(r"[^\w\s:/.-]+", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def _contains_phrase(text: str, phrase: str) -> bool:
    text_n, phrase_n = _normalize(text), _normalize(phrase)
    if not phrase_n:
        return False
    escaped = re.escape(phrase_n).replace(r"\ ", r"\s+")
    return bool(re.search(r"(?<!\w)" + escaped + r"(?!\w)", text_n, re.UNICODE))


def _score_intent(text: str, patterns: Iterable[tuple[str, float]]) -> tuple[float, list[str]]:
    matches = [(p, w) for p, w in patterns if _contains_phrase(text, p)]
    if not matches:
        return 0.0, []
    score = sum(w * (1.0 + min(len(_normalize(p)) / 40.0, 0.75)) for p, w in matches)
    return score, [p for p, _ in matches]


def _extract_language(text: str) -> str | None:
    for language, aliases in _LANGUAGE_ALIASES.items():
        if any(_contains_phrase(text, alias) for alias in aliases):
            return language
    return None


def _extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s<>]+", text)



def _extract_topic(text: str) -> str | None:
    for pattern in (
        r"(?:یاد بگیر|یادگیری|مطالعه کن|study|learn)\s+(?:درباره|در مورد|about)?\s*(.+?)(?:\s+(?:و بعد|بعدش|سپس|then|and then)\s+|$)",
        r"(?:topic|موضوع)\s*[:=]\s*(.+)$",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip(" .،,؛;:")
            if value:
                return value[:200]
    return None


def _extract_goal(text: str) -> str | None:
    for pattern in (
        r"(?:کد بنویس|کدنویسی کن|برنامه بنویس|پروژه بساز|یک پروژه بساز|یه پروژه بساز|api بساز|write code|generate code|build a project|create a project)\s*(?:برای|for)?\s*(.+)$",
        r"(?:goal|هدف)\s*[:=]\s*(.+)$",
    ):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip(" .،,؛;:")
            if value:
                return value[:300]
    return None


def _extract_project_path(text: str) -> str | None:
    raw = str(text)
    direct = re.findall(r"(?:/projects/|/workspace/)[A-Za-z0-9._~/-]+", raw, re.IGNORECASE)
    if direct:
        return direct[0][:500]
    candidates = re.findall(r"(?:(?:[A-Za-z]:[\\/])|\\\\)[^\\s<>]+", raw)
    for candidate in candidates:
        candidate = candidate.rstrip(".,،؛;:)\"'")
        if candidate and any(token in candidate.casefold() for token in ("\\projects\\", "\\workspace\\")):
            return candidate[:500]
    return None


def _llm_classify(text: str, context: str | None = None) -> Intent | None:
    """Primary structured router. The returned intent is never authorization."""
    if getattr(settings, "router_llm_enabled", True) is False:
        return None
    try:
        from ..llm import create_llm
        allowed = {"chat", "learning", "coding", "code_execution", "security_scan",
                   "file_analysis", "help", "self_update", "git_write",
                   "pentest_external", "self_repair"}
        schema = {
            "type": "object",
            "additionalProperties": False,
            "required": ["primary", "intents", "confidence", "language", "topic", "goal"],
            "properties": {
                "primary": {"type": "string", "enum": sorted(allowed)},
                "intents": {"type": "array", "items": {"type": "string", "enum": sorted(allowed)}},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "language": {"type": ["string", "null"]},
                "topic": {"type": ["string", "null"]},
                "goal": {"type": ["string", "null"]},
            },
        }
        prompt = (
            "Classify the request by semantic intent, not keywords. "
            "A question about an action is not an execution request. "
            "Return only the schema-constrained object. "
            f"USER: {text}\nCONTEXT: {context or ''}"
        )
        client = create_llm("routing")
        if hasattr(client, "structured_chat_json"):
            data = client.structured_chat_json(prompt, schema, system="You are a strict semantic router. Never grant permission.")
        else:
            raw = client.chat(prompt, system="You are a strict semantic router. JSON only.")
            data = _parse_router_payload(raw)
        primary = data.get("primary")
        if primary not in allowed:
            return None
        intents = tuple(x for x in data.get("intents", []) if x in allowed) or (primary,)
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
        args: dict[str, Any] = {}
        for key in ("language", "topic", "goal"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                args[key] = value.strip()[:300]
        urls = _extract_urls(text)
        if urls:
            args["urls"] = urls
        project_path = _extract_project_path(text)
        if project_path:
            args["project_path"] = project_path
        return Intent(primary, round(confidence, 3), primary in HIGH_RISK, args=args, intents=intents)
    except Exception:
        return None


def classify(text: str, context: str | None = None) -> Intent:
    """Semantic-first routing with deterministic safety fallback."""
    llm_intent = _llm_classify(text, context)
    if llm_intent is not None and llm_intent.confidence >= 0.55:
        return llm_intent

    message = _normalize(text)
    context_n = _normalize(context or "")
    scored = []
    for name, patterns in _INTENT_PATTERNS.items():
        score, matches = _score_intent(message, patterns)
        if score:
            scored.append((name, score, matches))
    if message in {"اجراش کن", "رانش کن", "run it", "execute it"} and any(
        token in context_n for token in ("کد", "code", "python", "javascript", "script")
    ):
        scored.append(("code_execution", 3.5, ["context:code"]))
    if not scored:
        return Intent("chat", 0.45, False, intents=("chat",))
    scored.sort(key=lambda item: (-item[1], -len(item[2][0]), item[0]))
    primary, score, matches = scored[0]
    selected = tuple(name for name, value, _ in scored if value >= score * 0.55)
    confidence = min(0.82, 0.45 + score / 10.0)
    args: dict[str, Any] = {}
    language = _extract_language(text)
    topic = _extract_topic(text)
    goal = _extract_goal(text)
    if language:
        args["language"] = language
    if topic:
        args["topic"] = topic
    if goal:
        args["goal"] = goal
    urls = _extract_urls(text)
    if urls:
        args["urls"] = urls
    project_path = _extract_project_path(text)
    if project_path:
        args["project_path"] = project_path
    return Intent(primary, round(confidence, 3), primary in HIGH_RISK, args=args, intents=selected or (primary,))

