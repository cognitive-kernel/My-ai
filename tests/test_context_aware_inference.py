from my_ai.domain.router import classify


class FakeRouter:
    def structured_chat_json(self, prompt, schema, system):
        current_user = prompt.split("CURRENT USER:", 1)[-1].split("CONVERSATION CONTEXT:", 1)[0]
        if "MQL4" in current_user or "فایل رو بساز" in current_user:
            return {"primary":"coding","intents":["coding"],"action":"create_artifact","confidence":0.99,"language":"MQL4","topic":None,"goal":"create artifact","project_path":None,"urls":[]}
        return {
            "primary": "chat",
            "intents": ["chat"],
            "action": "answer",
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


def test_agent_dispatches_coding_command_to_project_builder(monkeypatch):
    from my_ai.agent import Agent
    from my_ai.domain.router import Intent

    calls = {}

    def fake_build_project(goal, language, **kwargs):
        calls["goal"] = goal
        calls["language"] = language
        calls["kwargs"] = kwargs
        return {
            "status": "built",
            "language": language,
            "project_path": kwargs.get("project_path"),
            "project_name": "indicator",
            "files": ["main.mq4"],
            "build": {"passed": True},
            "tests": {"passed": True},
            "lint": {"passed": True},
        }

    monkeypatch.setattr("my_ai.agent.build_project", fake_build_project)
    intent = Intent(
        "coding",
        0.99,
        False,
        {
            "language": "MQL4",
            "project_path": r"D:\Projects\MY-AI\projects",
            "goal": "build indicator",
            "action": "create_artifact",
        },
        ("coding",),
    )

    assert Agent._project_build_requested("اندیکاتور MQL4 بنویس و ذخیره کن", intent)
    answer = Agent()._build_project_from_intent("اندیکاتور MQL4 بنویس و ذخیره کن", intent)

    assert calls["goal"] == "اندیکاتور MQL4 بنویس و ذخیره کن"
    assert calls["language"] == "MQL4"
    assert calls["kwargs"]["project_path"] == r"D:\Projects\MY-AI\projects"
    assert "پروژه ساخته و تست شد" in answer
