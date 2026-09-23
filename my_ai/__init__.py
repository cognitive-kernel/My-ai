__version__ = "0.2.0"

# The API module is the application entry point used by uvicorn.  Register the
# optional settings router only after that module has finished creating `app`,
# avoiding circular imports while keeping feature code separated from api.py.
import importlib.abc
import importlib.machinery
import sys


class _ApiFeatureFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname != "my_ai.api":
            return None
        try:
            sys.meta_path.remove(self)
        except ValueError:
            pass
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None or spec.loader is None:
            return spec
        original_loader = spec.loader

        class _Loader(importlib.abc.Loader):
            def create_module(self, module_spec):
                create = getattr(original_loader, "create_module", None)
                return create(module_spec) if create else None

            def exec_module(self, module):
                original_loader.exec_module(module)
                from .settings_feature import install
                install(module.app)

        spec.loader = _Loader()
        return spec


if not any(type(x).__name__ == "_ApiFeatureFinder" for x in sys.meta_path):
    sys.meta_path.insert(0, _ApiFeatureFinder())
