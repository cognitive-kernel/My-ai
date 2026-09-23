__version__ = "0.2.0"


def _install_app_features_on_startup():
    from .scheduler import StudyScheduler
    original = StudyScheduler.start_review_monitor
    if getattr(original, "_myai_features_wrapped", False):
        return

    def start_review_monitor_with_features(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        import sys
        api_module = sys.modules.get("my_ai.api")
        if api_module is not None and hasattr(api_module, "app"):
            from .settings_feature import install
            install(api_module.app)
        return result

    start_review_monitor_with_features._myai_features_wrapped = True
    StudyScheduler.start_review_monitor = start_review_monitor_with_features


_install_app_features_on_startup()
