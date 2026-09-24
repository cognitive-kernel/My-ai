from __future__ import annotations

import uvicorn

from .api import app, scheduler
from .auth import audit, require_user
from .config import settings
from .feature_routes import register_routes

register_routes(app, scheduler, require_user, audit)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port)
