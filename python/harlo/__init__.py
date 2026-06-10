"""Harlo — biologically-architected AI memory and action system."""

__version__ = "0.1.5"

# The Rust hot path is optional at import time (D56/B3): pure-Python
# engine work (trajectory sim, predictor training, schemas) must import
# cleanly on a venv without the compiled extension. Modules that need
# the hot path import harlo.hippocampus directly and fail honestly at
# the point of use.
try:
    from harlo.hippocampus import (
        py_recall,
        py_store_trace,
        py_microglia,
        py_consolidate,
        py_lookup_reflex,
        py_store_reflex,
        py_boost,
    )
except ImportError:  # pragma: no cover — no compiled hippocampus .so
    __all__ = ["__version__"]
else:
    __all__ = [
        "__version__",
        "py_recall",
        "py_store_trace",
        "py_microglia",
        "py_consolidate",
        "py_lookup_reflex",
        "py_store_reflex",
        "py_boost",
    ]
