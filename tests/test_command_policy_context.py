from my_ai.command_policy import parse_command


def test_file_build_followup_is_build_request():
    policy = parse_command("فایل رو بساز بر اساس دستوراتی که دادم و مسیرش رو بده")
    assert policy.build is True


def test_mql4_and_metatrader_are_detected():
    assert parse_command("برای متاتریدر 4 با MQL4 بساز").language == "MQL4"
