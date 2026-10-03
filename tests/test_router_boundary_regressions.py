import json

from my_ai.domain.router import classify


class FakeClassifier:
    def __init__(self, payload):
        self.payload = payload

    def structured_chat_json(self, message, schema, system=None):
        return dict(self.payload)


def base_payload(**overrides):
    payload = {
        "primary": "chat",
        "intents": ["chat"],
        "action": "answer",
        "confidence": 1.7,
        "language": None,
        "topic": None,
        "goal": None,
        "project_path": None,
        "urls": [],
    }
    payload.update(overrides)
    return payload


def test_router_normalizes_provider_confidence_out_of_range():
    result = classify("هر متنی", classifier=FakeClassifier(base_payload()))
    assert result.confidence == 1.0


def test_router_does_not_treat_non_execution_high_risk_intent_as_execution():
    result = classify(
        "بله اجازه دسترسی به فایل‌ها را داری و بررسی کن",
        classifier=FakeClassifier(base_payload(primary="database_import", intents=["database_import"], action="answer", confidence=0.9)),
    )
    assert result.name == "chat"
    assert result.args["action"] == "answer"
