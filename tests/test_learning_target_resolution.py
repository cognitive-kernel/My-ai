from my_ai.dynamic_learning import resolve_learning_target


def test_short_c_alias_still_resolves_to_c():
    assert resolve_learning_target("C یاد بگیر") == "C"
    assert resolve_learning_target("learn C") == "C"
