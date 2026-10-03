from pathlib import Path
import re

import pytest

from my_ai.roadmap_catalog import roadmap_option_sections, roadmap_options
from my_ai.settings_feature import router

pytestmark = pytest.mark.timeout(30)


def _roadmap_path() -> Path:
    return Path(__file__).resolve().parents[1] / "docs" / "نقشه جامع توسعه و مدیریت بدون کدنویسی.md"


def test_roadmap_catalog_contains_every_checked_item():
    source = _roadmap_path().read_text(encoding="utf-8")
    expected = []
    section = "نقشه توسعه"
    for line in source.splitlines():
        heading = re.match(r"^#{2,3}\s+(.+?)\s*$", line)
        if heading:
            section = heading.group(1).replace("*", "").replace(chr(96), "").strip()
        match = re.match(r"^\*\*\[x\]\s+(.+?)\*\*", line)
        if match:
            expected.append((section, match.group(1).strip()))
    actual = [(x["section"], x["title"]) for x in roadmap_options()]
    assert actual == expected
    assert len(actual) >= 250


def test_settings_exposes_roadmap_options_route():
    paths = {getattr(route, "path", "") for route in router.routes}
    assert "/settings/roadmap-options" in paths
    assert sum(len(x["items"]) for x in roadmap_option_sections()) == len(roadmap_options())


def test_settings_page_and_script_render_roadmap_options():
    root = Path(__file__).resolve().parents[1]
    html = (root / "my_ai" / "settings_feature.py").read_text(encoding="utf-8")
    js = (root / "my_ai" / "settings_script.js").read_text(encoding="utf-8")
    assert "id='roadmap-options'" in html
    assert "id='roadmap-options-list'" in html
    assert "loadRoadmapOptions" in js
    assert "/settings/roadmap-options" in js
    assert "checked disabled" in js
