from my_ai.command_policy import parse_command

def test_pentest_defaults_to_fix():
    assert parse_command("از پروژه پن تست بگیر").security_action == "report"

def test_explicit_report_overrides_pentest_default():
    assert parse_command("پن تست بگیر و فقط گزارش بده").security_action == "report"

def test_generic_test_is_report_only():
    assert parse_command("از این پروژه تست بگیر").security_action == "report"

def test_explicit_fix_overrides_report():
    assert parse_command("تست بگیر و باگ‌ها را رفع کن").security_action == "fix"


def test_plain_test_command_is_security_report():
    p=parse_command("تست بگیر")
    assert p.security is True
    assert p.security_action == "report"


def test_language_is_detected():
    assert parse_command("write a Python program").language == "Python"

def test_generic_write_request_is_not_build_command():
    assert parse_command("please write a summary").build is False


def test_program_generation_is_not_build_command():
    assert parse_command("برنامه بنویس").build is False
    assert parse_command("write a program").build is False
    assert parse_command("write code").build is False


def test_project_build_request_is_build_command():
    assert parse_command("build project").build is True
    assert parse_command("build application").build is True


def test_project_generation_in_persian_remains_an_action_request_without_build_execution():
    assert parse_command("یک برنامه Python برای مدیریت فایل‌ها بنویس").build is False
