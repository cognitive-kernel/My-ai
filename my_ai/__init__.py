from pathlib import Path
import sys
import logging

__version__ = "0.2.0"
logger = logging.getLogger(__name__)

try:
    from . import settings_feature as _settings_feature
    _settings_script = Path(__file__).with_name("settings_script.js")
    if _settings_script.is_file():
        _settings_feature.SETTINGS_JS = _settings_script.read_text(encoding="utf-8")
except Exception as exc:
    logger.warning("SETTINGS_UI_BOOTSTRAP_FAILED: %s", exc)

try:
    from . import ui as _ui
    from . import ui_extensions as _ui_extensions
    _ui_extensions_inject = getattr(_ui_extensions, "INJECT", "")
    if 'id="localFileTools"' not in _ui.HTML:
        _ui.HTML = _ui.HTML.replace("</body>", _ui_extensions_inject + "</body>")
except Exception as exc:
    logger.warning("UI_EXTENSION_BOOTSTRAP_FAILED: %s", exc)

try:
    from . import agent_runtime as _agent_runtime
    sys.modules[__name__ + ".agent"] = _agent_runtime
    agent = _agent_runtime
except Exception as exc:
    logger.warning("AGENT_RUNTIME_BOOTSTRAP_FAILED: %s", exc)

def page():
    return _ui.HTML
