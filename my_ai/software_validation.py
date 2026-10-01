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

    lifecycle = {"install", "build", "test", "lint", "typecheck", "run"}
    for index, requirement in enumerate(plan.get("tool_requirements") or []):
        if not isinstance(requirement, dict):
            raise SoftwareValidationError(f"Tool requirement {index} is not an object.")
        commands = requirement.get("commands") or {}
        if not isinstance(commands, dict) or any(key not in lifecycle for key in commands):
            raise SoftwareValidationError(f"Tool requirement {index} contains non-lifecycle command keys.")
        providers = requirement.get("providers")
        if providers is not None:
            if not isinstance(providers, list) or not providers:
                raise SoftwareValidationError(f"Tool requirement {index} providers must be a non-empty list.")
            for provider_index, provider in enumerate(providers):
                if not isinstance(provider, dict) or not provider.get("executables"):
                    raise SoftwareValidationError(f"Tool provider {index}:{provider_index} must declare host executables.")
                provider_commands = provider.get("commands") or {}
                if any(key not in lifecycle for key in provider_commands):
                    raise SoftwareValidationError(f"Tool provider {index}:{provider_index} contains non-lifecycle command keys.")
                install = provider.get("install")
                if install is not None and (not isinstance(install, dict) or set(install) - {"manager", "package"}):
                    raise SoftwareValidationError(f"Tool provider {index}:{provider_index} contains unsafe installation metadata.")
        install = requirement.get("install")
        if install is not None and (not isinstance(install, dict) or set(install) - {"manager", "package"}):
            raise SoftwareValidationError(f"Tool requirement {index} contains unsafe installation metadata.")


def validation_matrix_requirements(plan: dict[str, Any], language: str | None) -> list[str]:
    """Return validation capabilities required by the resolved artifact."""
    lang = str(language or "").strip().casefold()
    artifact = re.sub(r"[\\s_-]+", " ", str(plan.get("artifact_type") or "").casefold()).strip()
    requirements = ["build", "test", "lint", "typecheck", "run"]
    if lang in {"rust", "rs"}:
        requirements.append("clippy")
    if lang in {"python", "py"}:
        requirements.append("strict_typecheck")
    if lang in {"javascript", "typescript", "js", "ts"}:
        requirements.append("browser_e2e" if any(x in artifact for x in ("web", "website", "frontend", "browser", "ui")) else "typecheck")
    if lang in {"mql4", "mql5"}:
        requirements.append("compiler")
    if any(x in artifact for x in ("web", "website", "web application", "frontend")):
        requirements.append("browser_e2e")
    return list(dict.fromkeys(requirements))


def validate_validation_matrix(plan: dict[str, Any], language: str | None) -> list[str]:
    """Reject plans that omit required language/artifact-specific validation."""
    errors: list[str] = []
    declared = plan.get("tool_requirements") or []
    commands: dict[str, str] = {}
    for item in declared:
        if not isinstance(item, dict):
            continue
        raw_values = item.get("commands")
        values = raw_values if isinstance(raw_values, dict) else {}
        for key, value in values.items():
            if isinstance(value, str):
                commands[key] = value
            elif isinstance(value, list) and value:
                commands[key] = " ".join(str(x) for x in value)
    lang = str(language or "").strip().casefold()
    artifact = re.sub(r"[\\s_-]+", " ", str(plan.get("artifact_type") or "").casefold()).strip()
    for key in ("build", "test", "lint", "typecheck", "run"):
        if key not in commands:
            errors.append(f"Missing required lifecycle validation command: {key}")
    if lang in {"rust", "rs"} and "clippy" not in (commands.get("lint") or "").casefold():
        errors.append("Rust validation requires clippy in the lint command.")
    if lang in {"python", "py"} and not any(token in (commands.get("typecheck") or "").casefold() for token in ("mypy", "pyright")):
        errors.append("Python validation requires an explicit mypy or pyright typecheck command.")
    if lang in {"python", "py"} and "compileall" not in ((commands.get("build") or "") + " " + (commands.get("test") or "")).casefold():
        errors.append("Python validation requires explicit compile validation (compileall).")
    if lang in {"python", "py"} and "pytest" not in (commands.get("test") or "").casefold():
        errors.append("Python validation requires pytest execution.")
    if lang in {"javascript", "js", "typescript", "ts"} and not any(token in (commands.get("typecheck") or "").casefold() for token in ("tsc", "typecheck")):
        errors.append("JavaScript/TypeScript validation requires an explicit typecheck command.")
    if any(x in artifact for x in ("web", "website", "frontend", "browser")) and not any(token in (commands.get("run") or "").casefold() for token in ("playwright", "cypress", "browser", "e2e")):
        errors.append("Web validation requires an explicit browser/E2E runtime command.")
    if lang in {"mql4", "mql5"}:
        build_command = (commands.get("build") or "").casefold()
        if not any(token in build_command for token in ("metaeditor", "metalang")):
            errors.append("MQL validation requires an explicit compiler/toolchain build command.")
    if lang in {"javascript", "typescript", "js", "ts"} and not commands.get("install"):
        errors.append("JavaScript/TypeScript validation requires an explicit dependency installation command.")
    if lang in {"php"}:
        if "php -l" not in (commands.get("lint") or "").casefold():
            errors.append("PHP validation requires php -l syntax validation.")
        if any(x in artifact for x in ("laravel", "symfony")) and not any(x in (commands.get("test") or "").casefold() for x in ("artisan test", "phpunit", "symfony")):
            errors.append("PHP framework validation requires the framework test suite.")
        if not commands.get("test"):
            errors.append("PHP validation requires a test command or framework test suite.")
    return errors



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
