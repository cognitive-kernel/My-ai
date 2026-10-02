import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("exception_audit", Path(__file__).parents[1] / "scripts" / "exception_audit.py")
exception_audit = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(exception_audit)

def test_no_silent_exception_handlers():
    risky = [item for item in exception_audit.audit() if not item["handled"]]
    assert risky == [], "silent exception handlers: " + repr(risky)
