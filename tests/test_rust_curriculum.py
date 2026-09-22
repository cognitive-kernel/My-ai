from my_ai.curriculum import LANGUAGE_CURRICULA, LANGUAGE_ALIASES, LANGUAGE_SOURCES

def test_rust_curriculum_is_beginner_to_expert():
    topics=LANGUAGE_CURRICULA["Rust"]
    assert len(topics) >= 40
    names={x["topic"] for x in topics}
    for required in ["Ownership","Lifetimes","Async Rust","Unsafe Rust","FFI and systems programming","Production architecture","Expert Rust capstone"]:
        assert required in names

def test_rust_alias_and_sources():
    assert LANGUAGE_ALIASES["rust"]=="Rust"
    assert any("rust-lang.org" in url for url in LANGUAGE_SOURCES["Rust"])
