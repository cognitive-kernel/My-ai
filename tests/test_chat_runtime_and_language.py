from my_ai.domain.router import classify
from my_ai.ui import page


class FakeRouter:
    def __init__(self, language):
        self.language = language

    def structured_chat_json(self, *args, **kwargs):
        return {
            "primary": "coding",
            "intents": ["coding"],
            "action": "create_artifact",
            "confidence": 0.99,
            "language": self.language,
            "topic": "MetaTrader 4",
            "goal": "create indicator",
            "project_path": None,
            "urls": [],
        }


def test_router_does_not_use_ui_locale_as_artifact_language():
    intent = classify("یک اندیکاتور برای متاتریدر 4 بساز", classifier=FakeRouter("fa"))
    assert intent.args.get("language") is None


def test_router_preserves_actual_platform_language():
    intent = classify("یک اندیکاتور برای متاتریدر 4 بساز", classifier=FakeRouter("MQL4"))
    assert intent.args.get("language") == "MQL4"


def test_chat_page_uses_canonical_static_runtime():
    html = page()
    assert "myAiChatRuntimePatch" not in html
    assert "/chat/history?session_id=" in html
    assert "/chat/sessions?x=" in html
