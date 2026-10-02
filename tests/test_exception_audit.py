from scripts.exception_audit import audit

def test_no_silent_exception_handlers():
    risky = [item for item in audit() if not item["handled"]]
    assert risky == [], "silent exception handlers: " + repr(risky)
