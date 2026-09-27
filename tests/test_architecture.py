from pathlib import Path


def test_layered_packages_and_compatibility_facades_exist():
    for package in ("core", "domain", "application", "infra"):
        assert (Path("my_ai") / package).is_dir()
    assert "application-layer" in Path("my_ai/application/router.py").read_text(encoding="utf-8") or "Application service" in Path("my_ai/application/router.py").read_text(encoding="utf-8")
    assert "Compatibility facade" in Path("my_ai/router.py").read_text(encoding="utf-8") or "compatibility facade" in Path("my_ai/router.py").read_text(encoding="utf-8").lower()
    assert "Compatibility facade" in Path("my_ai/llm.py").read_text(encoding="utf-8")
    assert "Compatibility facade" in Path("my_ai/db.py").read_text(encoding="utf-8")
