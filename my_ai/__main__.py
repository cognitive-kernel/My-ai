from __future__ import annotations

import uvicorn
from .api import app
from .settings_store import get_int, get_setting


if __name__ == "__main__":
    host = str(get_setting("server.host", "127.0.0.1"))
    port = get_int("server.port", 8000)
    uvicorn.run(app, host=host, port=port)
