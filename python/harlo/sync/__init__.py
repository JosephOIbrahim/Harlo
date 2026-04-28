"""Path C sync layer — write-side dispatch between runtime tier and
persistence layer.

Per Phase 3 design + D4. Hot-path reads stay in runtime tier
(Constitution Law 4); the sync layer only routes mutations.

Imports `pxr` lazily via `harlo.usd_lite.persistence`. The sync
package itself can be imported without `[substrate]`; the strategy
modules import the persistence layer only when actually invoked.
"""
from __future__ import annotations

from . import checkpoint, write_through
from .checkpoint import Checkpoint, default_checkpoint
from .policy import Policy, POLICY_TABLE, resolve_policy

__all__ = [
    "Policy",
    "POLICY_TABLE",
    "resolve_policy",
    "write_through",
    "checkpoint",
    "Checkpoint",
    "default_checkpoint",
]
