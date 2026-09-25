from __future__ import annotations

import uvicorn

from .runtime_prerequisites import startup_check

# Check/install runtime prerequisites before importing optional application modules.
# Network is used only for this explicit prerequisite-install step.
startup_check()

from .api import app, scheduler
from .auth import audit, require_user
from .config import settings
from .custom_learning_resilience import install as install_custom_learning_resilience

register_routes(app, scheduler, require_user, audit)
install_learning_resilience()
install_custom_learning_resilience()
install_ui_extensions(app)


if __name__ == "__main__":
    uvicorn.run(app, host=settings.host, port=settings.port)
