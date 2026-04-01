"""LIVRPS layer / arc types for composition.

Layer priority (strongest to weakest):
  LOCAL > INHERIT > VARIANT > REFERENCE > PAYLOAD > SUBLAYER
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class ArcType(IntEnum):
    """LIVRPS arc types.  Lower numeric value = stronger opinion."""
    LOCAL = 1       # Strongest
    INHERIT = 2
    VARIANT = 3
    REFERENCE = 4
    PAYLOAD = 5
    SUBLAYER = 6    # Weakest


@dataclass
class Layer:
    """A single opinion layer in a composition stage."""
    arc_type: ArcType
    data: dict              # The layer's attribute data
    source: str             # Origin identifier
    timestamp: int          # Unix timestamp (seconds)
    layer_id: str           # Unique identifier

    def to_dict(self) -> dict:
        return {
            "arc_type": self.arc_type.value,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp,
            "layer_id": self.layer_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Layer:
        return cls(
            arc_type=ArcType(d["arc_type"]),
            data=d["data"],
            source=d["source"],
            timestamp=d["timestamp"],
            layer_id=d["layer_id"],
        )
