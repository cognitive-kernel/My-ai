from __future__ import annotations

from typing import Any


def install() -> None:
    from fastapi import FastAPI

    original_init = FastAPI.__init__
    if getattr(original_init, "_myai_feature_bootstrap", False):
        return

    def init_with_features(self: Any, *args: Any, **kwargs: Any) -> None:
        original_init(self, *args, **kwargs)
        from .settings_feature import install as install_features
        install_features(self)

    setattr(init_with_features, "_myai_feature_bootstrap", True)
    FastAPI.__init__ = init_with_features  # type: ignore[method-assign]
