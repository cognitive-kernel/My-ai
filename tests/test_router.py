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


def payload(primary="chat", intents=None, confidence=0.9, language=None, topic=None, goal=None, project_path=None, urls=None):
    return {
        "primary": primary, "intents": intents or [primary], "confidence": confidence,
        "language": language, "topic": topic, "goal": goal,
        "project_path": project_path, "urls": urls or [],
    }


def test_semantic_router_distinguishes_question_from_command():
    question, _ = route(payload("help", ["help"], 0.94, goal="explain how to run code"), "چطور کد را اجرا کنم؟")
    command, _ = route(payload("code_execution", ["code_execution"], 0.96), "این کد را اجرا کن")
    assert question.name == "help"
    assert command.name == "code_execution"
    assert command.requires_confirmation is True


def test_ambiguous_multi_intent_request_preserves_all_intents():
    result, fake = route(payload("learning", ["learning", "coding"], 0.91, "fa", "Python", "learn then implement"), "پایتون را یاد بگیر و بعد یک API بساز")
    assert result.name == "learning"
    assert result.intents == ("learning", "coding")
    assert result.args["language"] == "fa"
    assert result.args["topic"] == "Python"
    assert len(fake.calls) == 1


def test_high_risk_confirmation_is_derived_outside_model_authorization():
    result, _ = route(payload("git_write", ["git_write"], 0.98), "در مخزن تغییر بده")
    assert result.requires_confirmation is True


def test_structured_arguments_are_preserved():
    result, _ = route(payload("coding", ["coding"], 0.93, "python", None, "build API", "/projects/demo", ["https://example.com/spec"]), "پروژه را بساز")
    assert result.args == {
        "language": "python", "goal": "build API",
        "project_path": "/projects/demo", "urls": ["https://example.com/spec"],
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
    payload_data = payload("code_execution", ["code_execution"], 0.99, "mql4", None, "write an indicator that can read MetaTrader data and place trades")
    result, _ = route(payload_data, "یه اندیکاتور MQL4 بنویس که قیمت، نمودار و زمان متاتریدر را بخواند و امکان انجام معامله داشته باشد")
    assert result.name == "coding"
    assert result.requires_confirmation is False
def test_mql4_source_request_stays_in_code_generation_path():
    payload_data = payload(
        "code_execution",
        ["code_execution"],
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
