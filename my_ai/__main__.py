from __future__ import annotations

import uvicorn

from .api import app, scheduler
from .auth import audit, require_user
from .config import settings
from .feature_routes import register_routes
from .ui_extensions import install_ui_extensions

register_routes(app, scheduler, require_user, audit)
install_ui_extensions(app)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port)
