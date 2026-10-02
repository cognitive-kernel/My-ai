from my_ai import registries


def test_prompt_and_policy_registries_are_versioned():
    captured = []
    monkey = lambda *args, **kwargs: captured.append((args, kwargs)) or {}
    original = registries.put_record
    registries.put_record = monkey
    try:
        registries.publish_prompt("prompt", "text", version="4")
        registries.publish_policy("policy", {"allow": False}, version="5")
    finally:
        registries.put_record = original
    assert captured[0][0][2]["version"] == "4"
    assert captured[1][0][2]["version"] == "5"
