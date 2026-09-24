from pathlib import Path

__version__ = "0.2.0"

# Keep the runtime-served Settings script identical to the source asset. The
# package import executes this initialization before application routes are
# registered, so stale bundled JavaScript cannot override the fixed asset.
try:
    from . import settings_feature as _settings_feature
    _settings_script = Path(__file__).with_name("settings_script.js")
    if _settings_script.is_file():
        _settings_feature.SETTINGS_JS = _settings_script.read_text(encoding="utf-8")
except Exception:
    # Settings remains importable even in minimal tooling environments where
    # optional runtime dependencies are not installed yet.
    pass

# Serve the extended local-file and learning-control UI regardless of whether
# the app is launched through `python -m my_ai` or directly through uvicorn.
try:
    from . import ui as _ui
    from .ui_extensions import INJECT as _ui_extensions_inject
    if 'id="localFileTools"' not in _ui.HTML:
        _ui.HTML = _ui.HTML.replace("</body>", _ui_extensions_inject + "</body>")
except Exception:
    # Keep the base UI importable in minimal tooling environments.
    pass

def page():
    return _ui.HTML
