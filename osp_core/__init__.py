# Lazy imports — allows crypto to work without pydantic installed
import importlib as _il

def __getattr__(name):
    if name in ("crypto", "models", "jcs"):
        return _il.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
