from __future__ import annotations

import uvicorn

from .runtime_prerequisites import startup_check

# Check/install runtime prerequisites before importing optional application modules.
startup_check()

from .api import app
from .config import settings


if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port)
