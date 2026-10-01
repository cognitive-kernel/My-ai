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
                if install is not None:
                    _validate_install_spec(install, f"Tool provider {index}:{provider_index}")
        install = requirement.get("install")
        if install is not None:
            _validate_install_spec(install, f"Tool requirement {index}")


def _validate_install_spec(spec: Any, label: str) -> None:
    """Validate model-supplied installation metadata before it reaches a package manager."""
    if not isinstance(spec, dict) or set(spec) - {"manager", "package"}:
        raise SoftwareValidationError(f"{label} contains unsafe installation metadata.")
    manager = str(spec.get("manager") or "").strip().casefold()
    package = str(spec.get("package") or "").strip()
    allowed_managers = {"apt-get", "brew", "choco", "winget"}
    if manager and manager not in allowed_managers:
        raise SoftwareValidationError(f"{label} specifies an unsupported installation manager.")
    if package and (len(package) > 160 or not re.fullmatch(r"[A-Za-z0-9._+@:/-]+", package)):
        raise SoftwareValidationError(f"{label} contains an invalid package identifier.")
    if not manager and not package:
        raise SoftwareValidationError(f"{label} must specify an installation manager or package.")


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
    """Reject plans that omit required language/artifact-specific validation.

    Provider alternatives are validated independently. Commands from different
    providers must never be merged into a synthetic lifecycle.
    """
    errors: list[str] = []
    declared = plan.get("tool_requirements") or []
    lifecycle = ("build", "test", "lint", "typecheck", "run")

    def command_map(item: dict[str, Any]) -> dict[str, str]:
        commands: dict[str, str] = {}
        raw = item.get("commands")
        if isinstance(raw, dict):
            for key, value in raw.items():
                if isinstance(value, str) and value.strip():
                    commands[key] = value
                elif isinstance(value, list) and value:
                    commands[key] = " ".join(str(x) for x in value if str(x).strip())
        return commands

    def provider_maps(item: dict[str, Any]) -> list[dict[str, str]]:
        providers = item.get("providers")
        if not isinstance(providers, list) or not providers:
            return [command_map(item)]
        maps: list[dict[str, str]] = []
        common = command_map(item)
        for provider in providers:
            if not isinstance(provider, dict):
                continue
            merged = dict(common)
            provider_commands = provider.get("commands")
            if isinstance(provider_commands, dict):
                for key, value in provider_commands.items():
                    if isinstance(value, str) and value.strip():
                        merged[key] = value
                    elif isinstance(value, list) and value:
                        merged[key] = " ".join(str(x) for x in value if str(x).strip())
            maps.append(merged)
        return maps or [common]

    command_sets = [commands for item in declared if isinstance(item, dict) for commands in provider_maps(item)]
    if not command_sets:
        command_sets = [{}]

    lang = str(language or "").strip().casefold()
    artifact = re.sub(r"[\s_-]+", " ", str(plan.get("artifact_type") or "").casefold()).strip()

    for provider_index, commands in enumerate(command_sets):
        suffix = f" (provider {provider_index + 1})" if len(command_sets) > 1 else ""
        for key in lifecycle:
            if key not in commands:
                errors.append(f"Missing required lifecycle validation command: {key}{suffix}")
        if lang in {"rust", "rs"} and "clippy" not in (commands.get("lint") or "").casefold():
            errors.append(f"Rust validation requires clippy in the lint command{suffix}.")
        if lang in {"python", "py"} and not any(token in (commands.get("typecheck") or "").casefold() for token in ("mypy", "pyright")):
            errors.append(f"Python validation requires an explicit mypy or pyright typecheck command{suffix}.")
        if lang in {"python", "py"} and "compileall" not in ((commands.get("build") or "") + " " + (commands.get("test") or "")).casefold():
            errors.append(f"Python validation requires explicit compile validation (compileall){suffix}.")
        if lang in {"python", "py"} and "pytest" not in (commands.get("test") or "").casefold():
            errors.append(f"Python validation requires pytest execution{suffix}.")
        if lang in {"javascript", "js", "typescript", "ts"} and not any(token in (commands.get("typecheck") or "").casefold() for token in ("tsc", "typecheck")):
            errors.append(f"JavaScript/TypeScript validation requires an explicit typecheck command{suffix}.")
        if any(x in artifact for x in ("web", "website", "frontend", "browser")) and not any(token in (commands.get("run") or "").casefold() for token in ("playwright", "cypress", "browser", "e2e")):
            errors.append(f"Web validation requires an explicit browser/E2E runtime command{suffix}.")
        if lang in {"mql4", "mql5"}:
            build_command = (commands.get("build") or "").casefold()
            if not any(token in build_command for token in ("metaeditor", "metalang")):
                errors.append(f"MQL validation requires an explicit compiler/toolchain build command{suffix}.")
        if lang in {"javascript", "typescript", "js", "ts"} and not commands.get("install"):
            errors.append(f"JavaScript/TypeScript validation requires an explicit dependency installation command{suffix}.")
        if lang == "php":
            if "php -l" not in (commands.get("lint") or "").casefold():
                errors.append(f"PHP validation requires php -l syntax validation{suffix}.")
            if any(x in artifact for x in ("laravel", "symfony")) and not any(x in (commands.get("test") or "").casefold() for x in ("artisan test", "phpunit", "symfony")):
                errors.append(f"PHP framework validation requires the framework test suite{suffix}.")
            if not commands.get("test"):
                errors.append(f"PHP validation requires a test command or framework test suite{suffix}.")
    return list(dict.fromkeys(errors))



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
