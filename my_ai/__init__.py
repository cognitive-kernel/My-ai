__version__ = "0.2.0"


def _install_app_features() -> None:
    # `my_ai.api` is the ASGI entry point. Import it once, then register the
    # separated settings/learning feature against the fully-created FastAPI app.
    from . import api
    from .settings_feature import install

    install(api.app)


_install_app_features()
