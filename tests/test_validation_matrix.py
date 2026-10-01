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
