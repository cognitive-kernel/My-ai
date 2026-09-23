__version__ = "0.2.0"


def _install_app_features() -> None:
    from fastapi import FastAPI

    original_init = FastAPI.__init__
    if getattr(original_init, "_myai_features_wrapped", False):
        return

    def init_with_features(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        from .settings_feature import install
        install(self)

    init_with_features._myai_features_wrapped = True
    FastAPI.__init__ = init_with_features


_install_app_features()
