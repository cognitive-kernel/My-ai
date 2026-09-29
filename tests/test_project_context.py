def test_contextual_file_build_uses_previous_user_request(monkeypatch):
    from my_ai import project_builder

    monkeypatch.setattr(project_builder, "fetch_all", lambda *args: [
        {"id": 1, "language": "MQL4"},
    ] if "FROM chat_sessions" in args[0] else [
        {"role": "user", "content": "روی سیستمم متاتریدر 4 دارم؛ یک اندیکاتور MQL4 برای خواندن قیمت و نمودار و زمان و انجام معامله بساز."},
        {"role": "assistant", "content": "پاسخ قبلی اشتباه بود و JavaScript تولید کرد."},
        {"role": "user", "content": "فایل رو بساز بر اساس دستوراتی که دادم و مسیرش رو بده."},
    ])

    resolved, language, session_id = project_builder._recent_conversation_context(
        "فایل رو بساز بر اساس دستوراتی که دادم و مسیرش رو بده."
    )

    assert language == "MQL4"
    assert session_id == 1
    assert "متاتریدر 4" in resolved
    assert "JavaScript" in resolved


def test_contextual_build_does_not_replace_explicit_current_request(monkeypatch):
    from my_ai import project_builder

    monkeypatch.setattr(project_builder, "fetch_all", lambda *args: [
        {"id": 2, "language": "Rust"},
    ] if "FROM chat_sessions" in args[0] else [
        {"role": "user", "content": "یک پروژه قدیمی JavaScript داشتم."},
        {"role": "user", "content": "یک API جدید برای همان پروژه آماده کن."},
    ])

    resolved, language, _ = project_builder._recent_conversation_context("یک API جدید برای همان پروژه آماده کن.")
    assert language == "Rust"
    assert resolved.startswith("یک API جدید با Rust بساز.")
