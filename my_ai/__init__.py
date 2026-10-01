from pathlib import Path
import sys

__version__ = "0.2.0"

try:
    from . import settings_feature as _settings_feature
    _settings_script = Path(__file__).with_name("settings_script.js")
    if _settings_script.is_file():
        _settings_feature.SETTINGS_JS = _settings_script.read_text(encoding="utf-8")
except Exception:
    pass

try:
    from . import ui as _ui
    from . import ui_extensions as _ui_extensions
    _ui_extensions_inject = getattr(_ui_extensions, "INJECT", "")
    if 'id="localFileTools"' not in _ui.HTML:
        _ui.HTML = _ui.HTML.replace("</body>", _ui_extensions_inject + "</body>")
except Exception:
    pass

# Use one runtime chat implementation for every application import while keeping
# my_ai.agent as the legacy implementation available to agent_runtime itself.
try:
    from . import agent_runtime as _agent_runtime

    sys.modules[__name__ + ".agent"] = _agent_runtime
    agent = _agent_runtime
except Exception:
    pass

def page():
    return _ui.HTML
