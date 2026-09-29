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
ACTION_VALUES = ("answer", "explain", "analyze", "create_artifact", "modify_artifact", "execute", "inspect", "save", "report", "remediate", "continue_task", "confirm_high_risk")

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
    if not isinstance(data, dict):
        raise ValueError("Router output must be a JSON object.")
    required = tuple(ROUTER_SCHEMA["required"])
    if any(key not in data for key in required):
        raise ValueError("Router output is missing required fields.")
    if set(data) != set(required):
        raise ValueError("Router output contains unsupported fields.")
    if data["primary"] not in ALLOWED_INTENTS:
        raise ValueError("Router output contains an unsupported primary intent.")
    if not isinstance(data["intents"], list) or not data["intents"] or len(data["intents"]) > 5 or any(x not in ALLOWED_INTENTS for x in data["intents"]):
        raise ValueError("Router output contains unsupported intents.")
    confidence = data["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError("Router confidence must be between 0 and 1.")
    if not isinstance(data["urls"], list) or len(data["urls"]) > 10 or any(not isinstance(x, str) for x in data["urls"]):
        raise ValueError("Router URLs must be a list of strings.")
    for key in ("language", "topic", "goal", "project_path"):
        if data[key] is not None and not isinstance(data[key], str):
            raise ValueError(f"Router field {key} must be a string or null.")
    return data


def _intent_from_payload(data: dict[str, Any]) -> Intent:
    payload = _parse_router_payload(json.dumps(data, ensure_ascii=False))
    primary = payload["primary"]
    intents = tuple(dict.fromkeys(payload["intents"]))
    args = {key: payload[key] for key in ("action", "language", "topic", "goal", "project_path") if payload[key]}
    if payload["urls"]:
        args["urls"] = list(payload["urls"])
    # Authorization is derived from the complete semantic intent set, not from the model's primary label.
    requires_confirmation = bool(set(intents) & HIGH_RISK)
    return Intent(name=primary, confidence=round(float(payload["confidence"]), 3), requires_confirmation=requires_confirmation, args=args, intents=intents or (primary,))


def classify(text: str, context: str | None = None, classifier: StructuredRouter | None = None) -> Intent:
    if classifier is None:
        return Intent("chat", 0.0, False, args={"action": "answer"}, intents=("chat",))

    prompt = (
        "Classify the user's request semantically using the current conversation state. "
        "Do NOT use fixed trigger words or phrase lists. Infer the requested operation from meaning. "
        "The CURRENT USER message has highest priority; recent conversation is context for references. "
        "Choose exactly one action: answer, explain, analyze, create_artifact, modify_artifact, execute, inspect, save, continue_task, or confirm_high_risk. "
        "Infer actions from meaning, never from fixed trigger words. Use create_artifact when the user wants a new software/file/code deliverable, even when phrased indirectly. "
        "Use modify_artifact for changing an existing artifact. Use continue_task when the current message continues a prior task. "
        "Use confirm_high_risk only when the current message semantically approves a previously requested high-risk operation; do not require literal confirmation words. "
        "If conversation context shows a pending web-learning confirmation, classify an affirmative approval as learning + confirm_high_risk. "
        "For a coding creation request, primary should normally be coding, not code_execution. Never infer authorization. Return only the schema.\n"
        f"CURRENT USER: {text}\nCONVERSATION CONTEXT:\n{context or ''}"
    )
    data = classifier.structured_chat_json(
        prompt,
        ROUTER_SCHEMA,
        system="You are My-AI's context-aware semantic router. Understand intent from meaning, not trigger words. Output only schema-constrained routing data.",
    )
    if data.get("action") in {"create_artifact", "modify_artifact"} and data.get("primary") != "coding":
        intents = [x for x in data.get("intents", []) if x not in {"chat", "code_execution"}]
        intents.insert(0, "coding")
        data = {**data, "primary": "coding", "intents": list(dict.fromkeys(intents))[:5]}
    return _intent_from_payload(data)def classify(text: str, context: str | None = None, classifier: StructuredRouter | None = None) -> Intent:
    if classifier is None:
        return Intent("chat", 0.0, False, args={"action": "answer"}, intents=("chat",))

    prompt = (
        "Classify the user's request semantically using the current conversation state. "
        "Do NOT use fixed trigger words or phrase lists. Infer the requested operation from meaning. "
        "The CURRENT USER message has highest priority; recent conversation is context for references. "
        "Choose exactly one action: answer, explain, analyze, create_artifact, modify_artifact, execute, inspect, save, continue_task, or confirm_high_risk. "
        "Infer actions from meaning, never from fixed trigger words. Use create_artifact when the user wants a new software/file/code deliverable, even when phrased indirectly. "
        "Use modify_artifact for changing an existing artifact. Use continue_task when the current message continues a prior task. "
        "Use confirm_high_risk only when the current message semantically approves a previously requested high-risk operation; do not require literal confirmation words. "
        "If conversation context shows a pending web-learning confirmation, classify an affirmative approval as learning + confirm_high_risk. "
        "For a coding creation request, primary should normally be coding, not code_execution. Never infer authorization. Return only the schema.\n"
        f"CURRENT USER: {text}\nCONVERSATION CONTEXT:\n{context or ''}"
    )
    data = classifier.structured_chat_json(
        prompt,
        ROUTER_SCHEMA,
        system="You are My-AI's context-aware semantic router. Understand intent from meaning, not trigger words. Output only schema-constrained routing data.",
    )
    if data.get("action") in {"create_artifact", "modify_artifact"} and data.get("primary") != "coding":
        intents = [x for x in data.get("intents", []) if x not in {"chat", "code_execution"}]
        intents.insert(0, "coding")
        data = {**data, "primary": "coding", "intents": list(dict.fromkeys(intents))[:5]}
    return _intent_from_payload(data)
