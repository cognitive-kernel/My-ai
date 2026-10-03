from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import json
import re

from ..core.protocols import StructuredRouter

ALLOWED_INTENTS = frozenset({
    "chat", "learning", "coding", "code_execution", "security_scan", "file_analysis",
    "help", "self_update", "git_write", "pentest_external", "self_repair", "database_import", "image_generation",
})
HIGH_RISK = frozenset({"pentest_external", "git_write", "self_update", "database_import", "code_execution", "self_repair"})
ACTION_VALUES = ("answer", "explain", "analyze", "create_artifact", "modify_artifact", "execute", "inspect", "save", "continue_task")

ROUTER_SCHEMA: dict[str, Any] = {
    "type": "object", "additionalProperties": False,
    "required": ["primary", "intents", "action", "confidence", "language", "topic", "goal", "project_path", "urls"],
    "properties": {
        "primary": {"type": "string", "enum": sorted(ALLOWED_INTENTS)},
        "intents": {"type": "array", "items": {"type": "string", "enum": sorted(ALLOWED_INTENTS)}, "minItems": 1, "maxItems": 5},
        "action": {"type": "string", "enum": list(ACTION_VALUES)},
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
    return {"name": ROUTER_TOOL_SCHEMA["name"], "arguments": {"primary": intent.name, "intents": list(intent.intents or (intent.name,)), "action": intent.args.get("action", "answer"), "confidence": float(intent.confidence), "language": intent.args.get("language"), "topic": intent.args.get("topic"), "goal": intent.args.get("goal"), "project_path": intent.args.get("project_path"), "urls": list(intent.args.get("urls", []))}}

def _parse_router_payload(raw: str) -> dict[str, Any]:
    data = json.loads(raw)
    if not isinstance(data, dict): raise ValueError("Router output must be a JSON object.")
    required = tuple(ROUTER_SCHEMA["required"])
    if any(key not in data for key in required): raise ValueError("Router output is missing required fields.")
    if set(data) != set(required): raise ValueError("Router output contains unsupported fields.")
    if data["primary"] not in ALLOWED_INTENTS: raise ValueError("Router output contains an unsupported primary intent.")
    if not isinstance(data["intents"], list) or not data["intents"] or len(data["intents"]) > 5 or any(x not in ALLOWED_INTENTS for x in data["intents"]): raise ValueError("Router output contains unsupported intents.")
    confidence = data["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)): raise ValueError("Router confidence must be numeric.")
    # Some local structured-output providers ignore numeric bounds even when the schema declares them.
    # Keep routing dynamic while normalizing the model-generated scalar at the boundary.
    data["confidence"] = max(0.0, min(1.0, float(confidence)))
    if not isinstance(data["urls"], list) or len(data["urls"]) > 10 or any(not isinstance(x, str) for x in data["urls"]): raise ValueError("Router URLs must be a list of strings.")
    for key in ("language", "topic", "goal", "project_path"):
        if data[key] is not None and not isinstance(data[key], str): raise ValueError(f"Router field {key} must be a string or null.")
    return data

def _intent_from_payload(data: dict[str, Any]) -> Intent:
    payload = _parse_router_payload(json.dumps(data, ensure_ascii=False))
    primary = payload["primary"]
    intents = tuple(dict.fromkeys(payload["intents"]))
    args = {key: payload[key] for key in ("action", "language", "topic", "goal", "project_path") if payload[key]}
    if payload["urls"]: args["urls"] = list(payload["urls"])
    return Intent(name=primary, confidence=round(float(payload["confidence"]), 3), requires_confirmation=primary in HIGH_RISK, args=args, intents=intents or (primary,))

def _read_only_market_capability(text: str) -> dict[str, str] | None:
    """Resolve an explicit quote request without invoking the slow LLM router.
    
    This is a capability fast-path, not the general router: it only activates when
    the request contains a structured currency pair and an explicit read-only quote
    operation. All other requests still use semantic LLM routing.
    """
    raw = str(text or "").strip()
    low = raw.casefold()
    pair = re.search(r"\b([a-z]{3})\s*[/_-]\s*([a-z]{3})\b", low)
    if not pair:
        compact = re.search(r"\b(audusd|eurusd|gbpusd|usdjpy|usdchf|usdcad|nzdusd)\b", low)
        if compact:
            value = compact.group(1)
            pair = (value[:3], value[3:])
        else:
            return None
    if isinstance(pair, tuple):
        base, quote = pair
    else:
        base, quote = pair.group(1), pair.group(2)
    read_only_terms = ("قیمت", "نرخ", "quote", "bid", "ask", "price")
    if not any(term in low for term in read_only_terms):
        return None
    execution_terms = ("معامله", "سفارش", "خرید", "فروش", "trade", "order", "execute", "code", "کد", "اندیکاتور", "mql4", "mql5", "اکسپرت")
    if any(term in low for term in execution_terms):
        return None
    return {"symbol": f"{base}{quote}".upper(), "capability": "market.quote", "action": "answer"}


def classify(text: str, context: str | None = None, classifier: StructuredRouter | None = None) -> Intent:
    if classifier is None:
        return Intent("chat", 0.0, False, args={"action": "answer"}, intents=("chat",))

    fast_capability = _read_only_market_capability(text)
    if fast_capability is not None:
        return Intent(
            "chat",
            0.99,
            False,
            args=fast_capability,
            intents=("chat",),
        )

    prompt = (
        "Classify the user's request semantically using the current conversation state. "
        "Do NOT use fixed trigger words or phrase lists. Infer the requested operation from meaning. "
        "The CURRENT USER message has highest priority; recent conversation is context for references. "
        "Choose exactly one action: answer, explain, analyze, create_artifact, modify_artifact, execute, inspect, save, or continue_task. "
        "Use create_artifact when the user wants a new software/file/code deliverable, even when phrased indirectly. "
        "Use modify_artifact for changing an existing artifact. Use continue_task when the current message continues a prior task. "
        "For a coding creation request, primary should normally be coding, not code_execution. Never infer authorization. Return only the schema.\n"
        f"CURRENT USER: {text}\nCONVERSATION CONTEXT:\n{context or ''}"
    )
    data = classifier.structured_chat_json(
        prompt,
        ROUTER_SCHEMA,
        system="You are My-AI's context-aware semantic router. Understand intent from meaning, not trigger words. Output only schema-constrained routing data.",
    )
    action = data.get("action")
    if _is_read_only_market_query(text):
        data = {**data, "primary": "chat", "intents": ["chat"], "action": "answer", "confidence": max(float(data.get("confidence", 0.0)), 0.95)}
        action = "answer"
    if data.get("primary") in HIGH_RISK and action not in {"execute", "modify_artifact", "save"}:
        data = {**data, "primary": "chat", "intents": ["chat"], "action": action}
    if data.get("action") in {"create_artifact", "modify_artifact"} and data.get("primary") == "code_execution":
        data = {**data, "primary": "coding", "intents": ["coding" if x == "code_execution" else x for x in data.get("intents", [])]}
    return _intent_from_payload(data)
