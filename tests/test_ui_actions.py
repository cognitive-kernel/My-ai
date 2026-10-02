from my_ai.ui_actions import list_ui_actions


def test_ui_action_registry_has_safe_metadata():
    actions = list_ui_actions()
    assert actions
    ids = {item["id"] for item in actions}
    assert len(ids) == len(actions)
    for item in actions:
        assert item["method"] in {"GET", "POST"}
        assert item["endpoint"].startswith("/")
        assert item["permission"]
        assert item["module"]
        assert item["label"]
