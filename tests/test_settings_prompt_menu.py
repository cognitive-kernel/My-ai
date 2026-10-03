import pytest

pytestmark = pytest.mark.timeout(30)


def test_prompt_menu_has_dedicated_controls_and_runtime_actions():
    from my_ai.settings_feature import SETTINGS_HTML
    from my_ai import settings_feature
    from pathlib import Path
    script = Path('my_ai/settings_script.js').read_text(encoding='utf-8')

    assert "<h2>مدیریت قالب‌های پاسخ</h2>" in SETTINGS_HTML
    for marker in ("prompt_name", "prompt_task", "prompt_text", "prompt_test_input", "prompt_out"):
        assert marker in script
    for path in ("/settings/prompts",):
        assert any(getattr(route, "path", "") == path for route in settings_feature.router.routes)
    for marker in ("savePromptGUI()", "testPromptGUI()", "activatePromptGUI()"):
        assert marker in SETTINGS_HTML
