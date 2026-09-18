from my_ai.command_policy import parse_command

def test_pentest_defaults_to_fix():
    assert parse_command("از پروژه پن تست بگیر").security_action == "fix"

def test_explicit_report_overrides_pentest_default():
    assert parse_command("پن تست بگیر و فقط گزارش بده").security_action == "report"

def test_generic_test_is_report_only():
    assert parse_command("از این پروژه تست بگیر").security_action == "report"

def test_explicit_fix_overrides_report():
    assert parse_command("تست بگیر و باگ‌ها را رفع کن").security_action == "fix"
