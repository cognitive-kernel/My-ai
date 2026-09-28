from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import json

from ..core.protocols import StructuredRouter

ALLOWED_INTENTS = frozenset({
    "chat", "learning", "coding", "code_execution", "security_scan", "file_analysis",
    "help", "self_update", "git_write", "pentest_external", "self_repair", "database_import", "image_generation",
})
HIGH_RISK = frozenset({"pentest_external", "git_write", "self_update", "database_import", "code_execution", "self_repair"})
ROUTER_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["primary", "intents", "confidence", "language", "topic", "goal", "project_path", "urls"],
    "properties": {
        "primary": {"type": "string", "enum": sorted(ALLOWED_INTENTS)},
        "intents": {"type": "array", "items": {"type": "string", "enum": sorted(ALLOWED_INTENTS)}, "minItems": 1, "maxItems": 5},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "language": {"type": ["string", "null"]}, "topic": {"type": ["string", "null"]},
        "goal": {"type": ["string", "null"]}, "project_path": {"type": ["string", "null"]},
        "urls": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
    },
}
ROUTER_TOOL_SCHEMA = {"name": "route_request", "description": "Return structured semantic intent and arguments. Never authorize execution.", "parameters": ROUTER_SCHEMA}

@dataclass(frozen=True)
class Intent:
    name: str
    confidence: float
    requires_confirmation: bool = False
    args: dict[str, Any] = field(default_factory=dict)
    intents: tuple[str, ...] = ()

def router_tool_call(intent: Intent) -> dict[str, Any]:
    return {"name": ROUTER_TOOL_SCHEMA["name"], "arguments": {"primary": intent.name, "intents": list(intent.intents or (intent.name,)), "confidence": float(intent.confidence), "language": intent.args.get("language"), "topic": intent.args.get("topic"), "goal": intent.args.get("goal"), "project_path": intent.args.get("project_path"), "urls": list(intent.args.get("urls", []))}}

def _parse_router_payload(raw: str) -> dict[str, Any]:
    data = json.loads(raw)
    if not isinstance(data, dict): raise ValueError("Router output must be a JSON object.")
    required = tuple(ROUTER_SCHEMA["required"])
    if any(key not in data for key in required): raise ValueError("Router output is missing required fields.")
    if set(data) != set(required): raise ValueError("Router output contains unsupported fields.")
    if data["primary"] not in ALLOWED_INTENTS: raise ValueError("Router output contains an unsupported primary intent.")
    if not isinstance(data["intents"], list) or not data["intents"] or len(data["intents"]) > 5 or any(x not in ALLOWED_INTENTS for x in data["intents"]): raise ValueError("Router output contains unsupported intents.")
    confidence = data["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1: raise ValueError("Router confidence must be between 0 and 1.")
    if not isinstance(data["urls"], list) or len(data["urls"]) > 10 or any(not isinstance(x, str) for x in data["urls"]): raise ValueError("Router URLs must be a list of strings.")
    for key in ("language", "topic", "goal", "project_path"):
        if data[key] is not None and not isinstance(data[key], str): raise ValueError(f"Router field {key} must be a string or null.")
    return data

def _intent_from_payload(data: dict[str, Any]) -> Intent:
    payload = _parse_router_payload(json.dumps(data, ensure_ascii=False))
    primary = payload["primary"]
    intents = tuple(dict.fromkeys(payload["intents"]))
    args = {key: payload[key] for key in ("language", "topic", "goal", "project_path") if payload[key]}
    if payload["urls"]: args["urls"] = list(payload["urls"])
    return Intent(name=primary, confidence=round(float(payload["confidence"]), 3), requires_confirmation=primary in HIGH_RISK, args=args, intents=intents or (primary,))

def _is_continuation(text: str) -> bool:
    low = " ".join(str(text or "").casefold().split())
    return any(x in low for x in ("همونو", "همان را", "همون را", "همین رو", "همین را", "همون فایل", "دستورات قبلی", "دستور قبلی", "ادامه بده", "بر اساس چیزی که گفتم", "بر اساس دستوراتی که دادم", "طبق چیزی که گفتم", "the previous instructions", "the previous request", "continue", "build it", "create it", "make it", "same file", "same project"))

def _is_actionable(text: str) -> bool:
    low = str(text or "").casefold()
    return any(x in low for x in ("بساز", "ایجاد کن", "تولید کن", "بنویس", "فایل بساز", "پروژه بساز", "write", "build", "create", "generate", "implement"))

def classify(text: str, context: str | None = None, classifier: StructuredRouter | None = None) -> Intent:
    if classifier is None: return Intent("chat", 0.0, False, intents=("chat",))
    prompt = (
        "Classify the user's request semantically using the current conversation state. "
        "The CURRENT USER message has highest priority; recent conversation is context for references. "
        "If the current message refers to a previous request, same file/project, or says build/create it, inherit the active task and do not classify it as a new unrelated question. "
        "For multi-step requests include every relevant intent in intents. Never infer authorization. Return only the schema.\n"
        f"CURRENT USER: {text}\nCONVERSATION CONTEXT:\n{context or ''}"
    )
    data = classifier.structured_chat_json(prompt, ROUTER_SCHEMA, system="You are My-AI's context-aware semantic router. Output only schema-constrained routing data.")
    text_low = text.casefold()
    explicit_execution = any(x in text_low for x in ("اجرا کن", "اجرایش کن", "اجرا بده", "run", "execute", "eval", "launch"))
    generation = _is_actionable(text)
    mql4_source = any(x in text_low for x in ("mql4", "mq4", "متاتریدر 4", "متاتریدر۴", "metatrader 4")) and generation
    if (mql4_source or (data.get("primary") == "code_execution" and generation)) and not explicit_execution:
        data = {**data, "primary": "coding", "intents": ["coding" if x == "code_execution" else x for x in data.get("intents", [])]}
    if _is_continuation(text) and not explicit_execution and data.get("primary") not in {"learning", "help", "image_generation", "security_scan", "pentest_external"}:
        intents = list(dict.fromkeys(["coding", *data.get("intents", [])])) if generation else list(dict.fromkeys([data.get("primary", "chat"), *data.get("intents", [])]))
        data = {**data, "primary": "coding" if generation else data.get("primary", "chat"), "intents": intents}
    return _intent_from_payload(data)
