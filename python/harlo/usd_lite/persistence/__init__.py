"""Path C persistence layer — real OpenUSD canonical storage.

Imports pxr only here. If [substrate] extra is not installed, the
module import fails with a clear error pointing to the install command.
Runtime tier (parent harlo.usd_lite package) does NOT import this module
and stays pxr-free per Constitution Law 3.
"""
from __future__ import annotations

try:
    from pxr import Sdf, Usd, Plug  # noqa: F401
except ImportError as exc:
    raise ImportError(
        "harlo.usd_lite.persistence requires the [substrate] extra. "
        "Install via: pip install -e .[substrate]  (or "
        "pip install \"usd-core>=24.05\" if the editable build "
        "fails on a .pyd file lock — see harness/path_c/substrate_pin.md)."
    ) from exc

from .writer import write
from .reader import read

__all__ = ["write", "read"]
