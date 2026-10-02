from pathlib import Path


def test_architecture_audit_and_regression_gate_are_present():
    assert Path("scripts/architecture_audit.py").exists()
    assert Path("scripts/architecture_e2e_audit.py").exists()
    assert Path("scripts/regression_gate.py").exists()
    assert Path("my_ai/test_runner.py").exists()
