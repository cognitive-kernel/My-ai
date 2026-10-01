from my_ai.software_validation import validate_validation_matrix


def plan(artifact="application"):
    return {
        "artifact_type": artifact,
        "tool_requirements": [{"commands": {
            "build": "build",
            "test": "test",
            "lint": "lint",
            "typecheck": "typecheck",
            "run": "run",
        }}],
    }


def test_python_requires_strict_typecheck():
    p = plan()
    p["tool_requirements"][0]["commands"]["typecheck"] = "mypy --strict ."
    p["tool_requirements"][0]["commands"]["build"] = "python -m compileall ."
    p["tool_requirements"][0]["commands"]["test"] = "python -m pytest"
    assert validate_validation_matrix(p, "Python") == []
    p["tool_requirements"][0]["commands"]["typecheck"] = "python -m compileall ."
    assert "Python validation requires" in " ".join(validate_validation_matrix(p, "Python"))


def test_rust_requires_clippy():
    p = plan()
    p["tool_requirements"][0]["commands"]["lint"] = "cargo clippy --all-targets --all-features -- -D warnings"
    assert validate_validation_matrix(p, "Rust") == []
    p["tool_requirements"][0]["commands"]["lint"] = "cargo fmt --check"
    assert "Rust validation requires clippy" in " ".join(validate_validation_matrix(p, "Rust"))


def test_web_requires_browser_e2e():
    p = plan("web application")
    p["tool_requirements"][0]["commands"]["typecheck"] = "tsc --noEmit"
    p["tool_requirements"][0]["commands"]["run"] = "npm run e2e:playwright"
    p["tool_requirements"][0]["commands"]["install"] = "npm ci"
    assert validate_validation_matrix(p, "TypeScript") == []
    p["tool_requirements"][0]["commands"]["run"] = "npm start"
    assert "browser/E2E" in " ".join(validate_validation_matrix(p, "TypeScript"))


def test_mql_requires_real_compiler_command():
    p = plan("expert advisor")
    p["tool_requirements"][0]["commands"]["build"] = "MetaEditor.exe /compile"
    assert validate_validation_matrix(p, "MQL4") == []
    p["tool_requirements"][0]["commands"]["build"] = "echo compile"
    assert "MQL validation requires" in " ".join(validate_validation_matrix(p, "MQL4"))

def test_python_validation_requires_compileall_and_pytest_even_with_strict_typecheck():
    p = plan()
    p["tool_requirements"][0]["commands"]["typecheck"] = "mypy --strict ."
    p["tool_requirements"][0]["commands"]["build"] = "python -m build"
    p["tool_requirements"][0]["commands"]["test"] = "python -m unittest"
    errors = validate_validation_matrix(p, "Python")
    assert "compileall" in " ".join(errors)
    assert "pytest" in " ".join(errors)


def test_provider_alternatives_cannot_form_a_synthetic_lifecycle():
    p = plan()
    p["tool_requirements"] = [{
        "providers": [
            {"executables": ["tool-a"], "commands": {
                "build": "tool-a build", "test": "tool-a test",
                "lint": "tool-a lint",
            }},
            {"executables": ["tool-b"], "commands": {
                "build": "tool-b build", "test": "tool-b test",
                "typecheck": "tool-b typecheck", "run": "tool-b run",
            }},
        ]
    }]
    errors = validate_validation_matrix(p, "Go")
    assert any("typecheck" in error and "provider 1" in error for error in errors)
    assert any("lint" in error and "provider 2" in error for error in errors)


def test_install_metadata_rejects_unsupported_manager_and_invalid_package():
    from my_ai.software_validation import SoftwareValidationError, validate_plan

    base = {
        "goal": "build app",
        "artifact_type": "application",
        "language": "Python",
        "requirements": ["app"],
        "architecture": ["application"],
        "phases": ["implement", "validate"],
        "acceptance_criteria": ["runs"],
        "research_queries": [],
        "validation": ["compile", "test"],
        "constraints": [],
        "ambiguities": [],
        "tool_requirements": [],
    }
    bad_manager = dict(base, tool_requirements=[{
        "install": {"manager": "shell", "package": "anything"}
    }])
    try:
        validate_plan(bad_manager)
    except SoftwareValidationError as exc:
        assert "manager" in str(exc).lower()
    else:
        raise AssertionError("unsupported installation manager was accepted")

    bad_package = dict(base, tool_requirements=[{
        "install": {"manager": "apt-get", "package": "python3;rm"}
    }])
    try:
        validate_plan(bad_package)
    except SoftwareValidationError as exc:
        assert "package" in str(exc).lower()
    else:
        raise AssertionError("unsafe package identifier was accepted")


def test_install_metadata_accepts_supported_package_identifier():
    from my_ai.software_validation import validate_plan

    validate_plan({
        "goal": "build app",
        "artifact_type": "application",
        "language": "Python",
        "requirements": ["app"],
        "acceptance_criteria": ["runs"],
        "research_queries": [],
        "validation": ["compile", "test"],
        "tool_requirements": [{
            "install": {"manager": "apt-get", "package": "python3.11"}
        }],
    })


def test_provider_alternatives_do_not_inherit_common_lifecycle_commands():
    p = plan()
    p["tool_requirements"] = [{
        "commands": {"lint": "shared-lint"},
        "providers": [
            {"executables": ["tool-a"], "commands": {
                "build": "tool-a build", "test": "tool-a test",
                "typecheck": "tool-a typecheck", "run": "tool-a run",
            }},
            {"executables": ["tool-b"], "commands": {
                "build": "tool-b build", "test": "tool-b test",
                "lint": "tool-b lint", "typecheck": "tool-b typecheck",
                "run": "tool-b run",
            }},
        ],
    }]
    errors = validate_validation_matrix(p, "Go")
    assert any("provider 1" in error and "lint" in error for error in errors)


def test_validate_plan_requires_complete_lifecycle_plan_shape():
    from my_ai.software_validation import SoftwareValidationError, validate_plan

    incomplete = {
        "goal": "build app",
        "artifact_type": "application",
        "language": "Python",
        "requirements": ["app"],
        "acceptance_criteria": ["runs"],
        "research_queries": [],
        "validation": ["compile", "test"],
    }
    try:
        validate_plan(incomplete)
    except SoftwareValidationError as exc:
        assert "architecture" in str(exc)
    else:
        raise AssertionError("incomplete semantic plan was accepted")
