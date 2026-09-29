from my_ai.domain.router import classify


class FakeClassifier:
    def structured_chat_json(self, message, schema, system=None):
        assert "trigger words" in message
        return {
            "primary": "coding",
            "intents": ["coding"],
            "action": "create_artifact",
            "confidence": 0.98,
            "language": "Python",
            "topic": "arcade game",
            "goal": "Create a playable point-eating game",
            "project_path": None,
            "urls": [],
        }


def test_indirect_creation_request_routes_to_software_artifact():
    intent = classify(
        "می‌خواهم یک بازی کوچک قابل اجرا داشته باشم که بازیکن با حرکت روی صفحه نقطه‌ها را جمع کند.",
        "کاربر قبلاً درباره محیط دسکتاپ صحبت کرده است.",
        FakeClassifier(),
    )
    assert intent.name == "coding"
    assert intent.args["action"] == "create_artifact"
    assert intent.args["language"] == "Python"
