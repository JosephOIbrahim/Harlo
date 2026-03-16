"""LIVRPS arc types for USD-Lite composition.

Layer priority (strongest to weakest):
  LOCAL > INHERIT > VARIANT > REFERENCE > PAYLOAD > SUBLAYER
"""

from __future__ import annotations

from enum import IntEnum


class ArcType(IntEnum):
    """LIVRPS arc types.  Lower numeric value = stronger opinion."""
    LOCAL = 1       # [L] Strongest -- direct local opinion
    INHERIT = 2     # [I] Inherited from parent prim
    VARIANT = 3     # [V] Variant layer (Hebbian deltas live here in Phase 5)
    REFERENCE = 4   # [R] Reference to external data
    PAYLOAD = 5     # [P] Payload data
    SUBLAYER = 6    # [S] Sublayer (weakest -- in-memory projection from SQLite)
