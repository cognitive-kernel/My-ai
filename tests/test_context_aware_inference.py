from my_ai.domain.router import classify


class FakeRouter:
    def structured_chat_json(self, prompt, schema, system):
        return {
            "primary": "chat",
            "intents": ["chat"],
            "confidence": 0.8,
            "language": None,
            "topic": None,
            "goal": None,
            "project_path": None,
            "urls": [],
        }


def test_previous_instruction_followup_routes_to_coding():
    intent = classify(
        "فایل رو بساز بر اساس دستوراتی که دادم",
        "موضوع جاری: اندیکاتور MQL4 برای MetaTrader 4\nآخرین درخواست: ساخت اندیکاتور",
        FakeRouter(),
    )
    assert intent.name == "coding"
    assert "coding" in intent.intents


def test_mql4_generation_is_not_code_execution():
    intent = classify(
        "برای MetaTrader 4 یک اندیکاتور MQL4 بنویس",
        "موضوع جاری: MetaTrader 4",
        FakeRouter(),
    )
    assert intent.name == "coding"
    assert "code_execution" not in intent.intents


def test_unrelated_chat_is_not_forced_into_coding():
    intent = classify("قیمت امروز چیست؟", "موضوع جاری: آب و هوا", FakeRouter())
    assert intent.name == "chat"
