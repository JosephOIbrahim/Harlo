"""USD bootstrap — ensure pxr is importable.

Adds USD 26.03 Python path and DLL directories to sys.path.
Must be imported before any pxr import.
"""

import os
import sys

USD_ROOT = r"C:\USD\26.03-exec"
USD_PYTHON = os.path.join(USD_ROOT, "lib", "python")
USD_LIB = os.path.join(USD_ROOT, "lib")
USD_BIN = os.path.join(USD_ROOT, "bin")


def bootstrap_usd() -> bool:
    """Add USD paths to sys.path and DLL directories.

    Returns True if pxr is importable after bootstrapping.
    """
    if USD_PYTHON not in sys.path:
        sys.path.insert(0, USD_PYTHON)

    try:
        os.add_dll_directory(USD_LIB)
        os.add_dll_directory(USD_BIN)
    except (OSError, AttributeError):
        pass

    try:
        from pxr import Usd  # noqa: F401
        return True
    except ImportError:
        return False


# Auto-bootstrap on import
USD_AVAILABLE = bootstrap_usd()
