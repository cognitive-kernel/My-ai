from pathlib import Path


def test_layered_packages_exist_and_domain_router_is_canonical():
    assert Path("my_ai/core/protocols.py").is_file()
    assert Path("my_ai/domain/router.py").is_file()
    text = Path("my_ai/router.py").read_text(encoding="utf-8")
    assert "Compatibility facade" in text
    assert "from .domain.router import" in text


def test_domain_router_does_not_depend_on_http_ui_layers():
    text = Path("my_ai/domain/router.py").read_text(encoding="utf-8")
    assert "from ..api" not in text
    assert "from ..static" not in text
