from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class SoftwareValidationError(ValueError):
    """Raised when a generated artifact contradicts its requested environment or role."""


def validate_plan(plan: dict[str, Any]) -> None:
    # Older integrations may return the original plan shape. Normalize harmless omissions;
    # the new planner schema still requires these fields from the model itself.
    plan.setdefault("artifact_type", "software project")
    plan.setdefault("constraints", [])
    plan.setdefault("ambiguities", [])
    required = ("goal", "artifact_type", "language", "requirements", "acceptance_criteria", "research_queries", "validation")
    missing = [key for key in required if key not in plan]
    if missing:
        raise SoftwareValidationError(f"Planner omitted required fields: {', '.join(missing)}")
    if not str(plan.get("goal") or "").strip():
        raise SoftwareValidationError("Planner produced an empty goal.")
    if not str(plan.get("artifact_type") or "").strip():
        raise SoftwareValidationError("Planner did not identify the artifact type.")
    if not plan.get("requirements") or not plan.get("acceptance_criteria"):
        raise SoftwareValidationError("Planner produced no testable requirements or acceptance criteria.")


def _read_text_files(workspace: Path) -> str:
    chunks: list[str] = []
    for path in workspace.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in {".mq4", ".mqh", ".py", ".php", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".java", ".kt", ".swift", ".c", ".h", ".cpp", ".cs", ".sql", ".html", ".css"}:
            continue
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n".join(chunks)


def validate_generated_project(workspace: Path, plan: dict[str, Any], language: str) -> list[str]:
    """Return concrete semantic defects that must be repaired before completion."""
    defects: list[str] = []
    text = _read_text_files(workspace)
    canonical = str(language or "").casefold()
    artifact = re.sub(r"[\s_-]+", " ", str(plan.get("artifact_type") or "").casefold()).strip()

    if canonical == "mql4":
        if not list(workspace.rglob("*.mq4")):
            defects.append("MQL4 task produced no .mq4 source file.")
        mql5_only = (r"#include\s*[<\"]Trade[\\/]Trade\.mqh[>\"]", r"\bCTrade\b", r"\bSymbolInfoTick\s*\(")
        for pattern in mql5_only:
            if re.search(pattern, text, re.IGNORECASE):
                defects.append("MQL4 source contains an MQL5-only API/header: " + pattern)
        if (artifact in {"indicator", "custom indicator", "mt4 indicator"} or "custom indicator" in artifact) and re.search(r"\bOrderSend\s*\(", text):
            defects.append("The generated artifact is declared as an MT4 custom indicator but contains OrderSend; trading capability must be implemented by an EA or script, not silently mixed into an indicator.")
        if artifact in {"expert advisor", "expert advisor (ea)", "ea", "mt4 expert advisor"}:
            if re.search(r"\bdouble\s+(Bid|Ask)\s*\[\s*\]\s*;", text) and re.search(r"\b(Bid|Ask)\s*=\s*iClose\s*\(", text):
                defects.append("MQL4 EA declares Bid/Ask as arrays and then assigns scalar prices; use MQL4 market-price values (Bid/Ask or MarketInfo) as scalars.")
            if re.search(r"\bif\s*\(\s*Bid\s*>\s*Ask\s*\)", text) or re.search(r"\bif\s*\(\s*Ask\s*>\s*Bid\s*\)", text):
                defects.append("MQL4 EA contains an impossible/inappropriate Bid-vs-Ask trading condition; do not invent a trade strategy when the user only requested terminal access.")
            if re.search(r"\bOrderSend\s*\(", text) and not re.search(r"\b(User|Manual|Enable|Allow|Trade|Trading)\w*\s*=\s*(true|false)", text, re.IGNORECASE):
                defects.append("MQL4 EA exposes trading without an explicit user-controlled enable/disable guard; trading must be opt-in when no strategy was specified.")

    placeholder_patterns = (r"TODO\b", r"FIXME\b", r"placeholder", r"ConditionToTrade\s*\(\)\s*\{\s*return\s+true\s*;?")
    for pattern in placeholder_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            defects.append(f"Generated project contains an unresolved placeholder: {pattern}")
    return defects
