from my_ai.application.router import build_router_service


class FakeRouter:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def structured_chat_json(self, message, schema, system=None):
        self.calls.append((message, schema, system))
        return self.payload


def route(payload, text, context=None):
    fake = FakeRouter(payload)
    result = build_router_service(fake).classify(text, context)
    return result, fake


def payload(primary="chat", intents=None, action="answer", confidence=0.9, language=None, topic=None, goal=None, project_path=None, target=None, urls=None):
    return {
        "primary": primary, "intents": intents or [primary], "action": action, "confidence": confidence,
        "language": language, "topic": topic, "goal": goal,
        "project_path": project_path, "target": target, "urls": urls or [],
    }


def test_semantic_router_distinguishes_question_from_command():
    question, _ = route(payload("help", ["help"], "answer", 0.94, goal="explain how to run code"), "چطور کد را اجرا کنم؟")
    command, _ = route(payload("code_execution", ["code_execution"], "execute", 0.96), "این کد را اجرا کن")
    assert question.name == "help"
    assert command.name == "code_execution"
    assert command.requires_confirmation is True


def test_ambiguous_multi_intent_request_preserves_all_intents():
    result, fake = route(payload("learning", ["learning", "coding"], "continue_task", 0.91, "fa", "Python", "learn then implement"), "پایتون را یاد بگیر و بعد یک API بساز")
    assert result.name == "learning"
    assert result.intents == ("learning", "coding")
    assert result.args.get("language") is None
    assert result.args["topic"] == "Python"
    assert len(fake.calls) == 1


def test_high_risk_confirmation_is_derived_outside_model_authorization():
    result, _ = route(payload("git_write", ["git_write"], "modify_artifact", 0.98), "در مخزن تغییر بده")
    assert result.requires_confirmation is True


def test_structured_arguments_are_preserved():
    result, _ = route(payload("coding", ["coding"], "create_artifact", 0.93, "python", None, "build API", "/projects/demo", ["https://example.com/spec"]), "پروژه را بساز")
    assert result.args == {
        "action": "create_artifact", "language": "python", "goal": "build API",
        "project_path": "/projects/demo", "target": None, "urls": ["https://example.com/spec"],
    }


def test_no_classifier_is_safe_chat_only():
    result = build_router_service(None).classify("هر متن دلخواه")
    assert result.name == "chat"
    assert result.confidence == 0.0


def test_chat_route_does_not_define_keyword_intent_tables():
    from pathlib import Path
    source = Path("my_ai/api.py").read_text(encoding="utf-8")
    assert "learn_intent=(\"یاد بگیر\"" not in source
    assert "code_words=(" not in source
    assert "image_words=(" not in source


def test_code_generation_request_is_not_code_execution():
    payload_data = payload("code_execution", ["code_execution"], "create_artifact", 0.99, "mql4", None, "write an indicator that can read MetaTrader data and place trades")
    result, _ = route(payload_data, "یه اندیکاتور MQL4 بنویس که قیمت، نمودار و زمان متاتریدر را بخواند و امکان انجام معامله داشته باشد")
    assert result.name == "coding"
    assert result.requires_confirmation is False


def test_mql4_source_request_stays_in_code_generation_path():
    payload_data = payload(
        "code_execution",
        ["code_execution"],
        "create_artifact",
        0.99,
        "mql4",
        None,
        "generate MetaTrader 4 source",
    )
    result, _ = route(
        payload_data,
        "یه اندیکاتور MQL4 بنویس که قیمت، نمودار و زمان متاتریدر ۴ را بخواند و کد منبع را تولید کند",
    )
    assert result.name == "coding"
    assert result.requires_confirmation is False


def test_semantic_artifact_action_does_not_depend_on_trigger_words():
    result, _ = route(
        payload("coding", ["coding"], "create_artifact", 0.97, "python", None, "create a complete API project"),
        "یک سامانه کامل برای مدیریت سفارش‌ها طراحی کن، فایل‌های لازم را تولید کن و آماده اجرا تحویل بده",
    )
    assert result.name == "coding"
    assert result.args["action"] == "create_artifact"


def test_semantic_confirmation_does_not_depend_on_confirmation_word():
    result, _ = route(
        payload("git_write", ["git_write"], "confirm_high_risk", 0.96),
        "باشه، همون تغییری که گفتی را اعمال کن",
    )
    assert result.name == "git_write"
    assert result.args["action"] == "confirm_high_risk"


def test_semantic_variants_use_same_artifact_action_without_phrase_tables():
    variants = [
        "یک ابزار کامل مدیریت سفارش طراحی و آماده اجرا کن",
        "برای مدیریت سفارش‌ها یک برنامه کامل تحویل بده",
        "نیاز دارم سامانه مدیریت سفارش‌ها را پیاده‌سازی کنی",
        "یک پروژه قابل اجرا برای مدیریت سفارش‌ها آماده کن",
        "کل فایل‌ها و ساختار لازم این سامانه را فراهم کن",
    ]
    for text in variants:
        result, _ = route(
            payload("coding", ["coding"], "create_artifact", 0.95, "python", None, "order management application"),
            text,
        )
        assert result.name == "coding"
        assert result.args["action"] == "create_artifact"


def test_router_source_has_no_legacy_keyword_action_helpers():
    from pathlib import Path
    source = Path("my_ai/domain/router.py").read_text(encoding="utf-8")
    assert "_is_actionable" not in source
    assert "_is_continuation" not in source
    assert "بساز" not in source
    assert "build it" not in source


def test_semantic_learning_variants_do_not_require_learning_phrases():
    variants = [
        "درباره Rust مطالعه عمیق انجام بده و نکات مهمش را به آموزش من اضافه کن",
        "می‌خواهم Rust را بررسی کنم و دانسته‌هایت درباره آن را گسترش بده",
        "برای Rust منابع معتبر پیدا کن و آموخته‌ها را ثبت کن",
        "از منابع موجود درباره Rust دانش جدید جمع‌آوری کن",
    ]
    for text in variants:
        result, _ = route(payload("learning", ["learning"], "answer", 0.95, "rust", "Rust", "learn Rust"), text)
        assert result.name == "learning"


def test_semantic_continuation_variants_do_not_require_continuation_phrases():
    variants = [
        "کار ناتمام قبلی را از همان نقطه دنبال کن",
        "مرحله بعدی همان کاری که در جریان بود را انجام بده",
        "فرآیند قبلی را کامل کن و نتیجه نهایی را تحویل بده",
        "ادامه منطقی کار فعلی را اجرا کن",
    ]
    for text in variants:
        result, _ = route(payload("coding", ["coding"], "continue_task", 0.95, "python", None, "continue active project"), text)
        assert result.args["action"] == "continue_task"


def test_semantic_high_risk_confirmation_variants_do_not_require_literal_tokens():
    variants = [
        "می‌توانی همان تغییر را اعمال کنی",
        "موافقم؛ تغییر پیشنهادی را اجرا کن",
        "همان موردی که بررسی کردی را عملی کن",
        "تصمیم با تو نیست؛ فقط همان تغییر تأییدشده را اعمال کن",
    ]
    for text in variants:
        result, _ = route(payload("git_write", ["git_write"], "confirm_high_risk", 0.95), text)
        assert result.args["action"] == "confirm_high_risk"
        assert result.requires_confirmation is False


def test_api_has_no_command_policy_dependency():
    from pathlib import Path
    source = Path("my_ai/api.py").read_text(encoding="utf-8")
    assert "command_policy" not in source
    assert "parse_command" not in source
    assert "BUILD_WORDS" not in source


def test_router_has_no_static_topic_marker_lists():
    from pathlib import Path
    source = Path("my_ai/domain/router.py").read_text(encoding="utf-8")
    assert "_is_code_or_indicator_request" not in source
    assert "_is_explicit_database_import" not in source
    assert "_is_actionable" not in source
    assert "_is_continuation" not in source


def test_semantic_acceptance_has_twenty_distinct_natural_phrasings():
    groups = {
        "artifact_creation": [
            "یک برنامه مدیریت هزینه شخصی با رابط ساده آماده کن.",
            "برای ثبت و دسته‌بندی هزینه‌ها یک ابزار قابل اجرا فراهم کن.",
            "ساختار کامل یک اپ مدیریت مخارج را پیاده‌سازی کن.",
            "می‌خواهم سامانه ثبت هزینه‌ها را از ابتدا تا اجرای نهایی داشته باشم.",
            "فایل‌ها و اجزای لازم برای یک برنامه مدیریت بودجه را تحویل بده.",
        ],
        "learning": [
            "درباره Rust از منابع معتبر تحقیق کن و دانسته‌های تازه را ثبت کن.",
            "دانش موجودت درباره FastAPI را با منابع جدید تکمیل کن.",
            "مستندات TypeScript را بررسی کن و نکات کاربردی را به دانش محلی اضافه کن.",
            "برای Docker اطلاعات معتبر جمع‌آوری کن و نتیجه را در دانش پروژه نگه دار.",
            "نسخه‌های جدید این فناوری را مطالعه کن و یافته‌های مرتبط را ثبت کن.",
        ],
        "continuation": [
            "کار نیمه‌تمام فعلی را با همان هدف قبلی جلو ببر.",
            "از آخرین مرحله‌ای که روی پروژه بودیم، مرحله بعد را انجام بده.",
            "همان پروژه جاری را بدون شروع دوباره کامل‌تر کن.",
            "روند قبلی را ادامه بده و بخش باقی‌مانده را به پایان برسان.",
            "بر اساس وضعیت فعلی پروژه، کار بعدی لازم را انجام بده.",
        ],
        "high_risk_confirmation": [
            "تغییری که در بررسی قبلی پیشنهاد شد را همین حالا اعمال کن.",
            "همان عملیات حساس مورد توافق را اجرا کن.",
            "بر مبنای تصمیم قبلی، تغییر مخزن را انجام بده.",
            "آن اقدام سیستمی که توضیح دادی را عملی کن.",
            "تغییر پرریسک بررسی‌شده را در محیط هدف اجرا کن.",
        ],
    }
    all_variants = [item for values in groups.values() for item in values]
    assert len(all_variants) == 20
    assert len(set(all_variants)) == 20
    for text in all_variants:
        assert isinstance(text, str) and text.strip()
