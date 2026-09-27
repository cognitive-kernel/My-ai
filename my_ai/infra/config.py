"""Infrastructure compatibility view of shared runtime configuration."""
from __future__ import annotations

from .. import config as _config


def __getattr__(name: str):
    return getattr(_config, name)


def __dir__():
    return sorted(set(globals()) | set(dir(_config)))
