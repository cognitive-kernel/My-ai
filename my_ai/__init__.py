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
