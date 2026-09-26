from my_ai.router import classify


def test_persian_learning_variants():
    assert classify("لطفاً به من پایتون آموزش بده").name == "learning"
    assert classify("درس پایتون رو شروع کن").name == "learning"


def test_execution_variants():
    assert classify("این کد رو ران کن").name == "code_execution"
    assert classify("اجراش کن").name == "code_execution"
    assert classify("run this code").name == "code_execution"


def test_self_update_variants():
    assert classify("آپدیت خودت رو انجام بده").name == "self_update"
    assert classify("self update کن").name == "self_update"


def test_coding_variants_and_overlap():
    assert classify("یک پروژه بساز").name == "coding"


def test_normalization_and_half_space():
    assert classify("لطفاً به من پایتون‌آموزش بده!").name == "learning"


def test_arguments_and_multi_intent():
    result = classify("پایتون یاد بگیر و بعد یک API بساز")
    assert result.args["language"] == "python"
    assert "learning" in result.intents
    assert "coding" in result.intents


def test_context_for_continuation():
    result = classify("اجراش کن", "این کد پایتون را آماده کردم")
    assert result.name == "code_execution"


def test_negative_execution_match():
    assert classify("چطور کد را اجرا کنم؟").name != "code_execution"


def test_high_risk_confirmation():
    assert classify("روی گیت تغییر بده").requires_confirmation is True


def test_chat_fallback():
    result = classify("امروز هوا چطور است؟")
    assert result.name == "chat"
    assert result.intents == ("chat",)


def test_self_repair_variants():
    assert classify("خودت را تعمیر کن").name == "self_repair"
    assert classify("fix yourself").name == "self_repair"
    assert classify("باگ خودتو درست کن").name == "self_repair"


def test_additional_learning_and_coding_variants():
    assert classify("ادامه یادگیری پایتون").name == "learning"
    assert classify("کد تولید کن").name == "coding"
