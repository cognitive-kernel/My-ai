from __future__ import annotations

import uvicorn
from .api import app
import os

from .settings_store import get_int, get_setting, has_setting


if __name__ == "__main__":
    configured_host = str(get_setting("server.host", "127.0.0.1"))
    host = configured_host if has_setting("server.host") else os.getenv("HOST", configured_host)
    port = get_int("server.port", 8000)
    uvicorn.run(app, host=host, port=port)
