from __future__ import annotations

import os
import shutil
import sys

import pytest

from my_ai.software_validation import SoftwareValidationError, validate_plan
from my_ai.tooling import _command, _parse_command, ensure_language_toolchain


def _base_plan() -> dict:
    return {
        "goal": "Build a small application",
        "artifact_type": "application",
        "language": "ExampleLanguage",
        "framework": None,
        "requirements": ["build the requested application"],
        "tool_requirements": [],
        "architecture": ["application"],
        "phases": ["implement", "validate"],
        "acceptance_criteria": ["the application builds successfully"],
        "research_queries": [],
        "validation": ["build"],
        "constraints": [],
        "ambiguities": [],
    }


def test_provider_alternatives_select_an_installed_provider(monkeypatch, tmp_path):
    executable = shutil.which("python") or shutil.which(sys.executable) or sys.executable
    executable_name = executable.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]

    requirements = [{
        "capabilities": ["compile or execute the project"],
        "providers": [
            {
                "executables": ["definitely-missing-provider"],
                "commands": {"build": ["definitely-missing-provider --build"]},
            },
            {
                "executables": [executable_name],
                "commands": {"build": [f"{executable_name} -c \"print(1)\""]},
            },
        ],
    }]

    result = ensure_language_toolchain(
        "UnseenLanguage",
        auto_install=False,
        requirements=requirements,
        cwd=str(tmp_path),
    )

    assert result["ready"] is True
    assert result["requirements"][0]["executables"] == [executable_name]
    assert result["requirements"][0]["commands"]["build"][0].startswith(executable_name)
    assert any(tool["executable"] == executable_name and tool["installed"] for tool in result["tools"])


def test_command_parser_rejects_shell_composition():
    with pytest.raises(ValueError):
        _parse_command("tool --build && tool --test")


def test_selected_provider_command_is_executable():
    executable = shutil.which("python") or shutil.which(sys.executable) or sys.executable
    executable_name = executable.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    requirements = [{
        "capabilities": ["execute"],
        "executables": [executable_name],
        "commands": {"run": [f"{executable_name} -c \"print(1)\""]},
    }]
    result = _command("UnseenLanguage", "run", requirements=requirements)
    assert os.path.basename(result[0]) == os.path.basename(executable) or result[0].endswith(executable_name)


def test_plan_rejects_non_lifecycle_tool_commands():
    plan = _base_plan()
    plan["tool_requirements"] = [{
        "capabilities": ["host tooling"],
        "commands": {"process_text": ["tool process"]},
        "executables": ["tool"],
    }]
    with pytest.raises(SoftwareValidationError):
        validate_plan(plan)


def test_plan_rejects_unsafe_install_metadata():
    plan = _base_plan()
    plan["tool_requirements"] = [{
        "capabilities": ["host tooling"],
        "commands": {"build": ["tool --build"]},
        "executables": ["tool"],
        "install": {"manager": "example", "command": "arbitrary shell"},
    }]
    with pytest.raises(SoftwareValidationError):
        validate_plan(plan)
