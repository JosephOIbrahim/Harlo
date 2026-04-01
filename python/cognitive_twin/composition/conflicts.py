"""Conflict detection for composition stages.

Identifies attributes where multiple layers provide differing values.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .layer import Layer
from .stage import MerkleStage


@dataclass
class Conflict:
    """A single attribute conflict across layers."""
    attribute: str
    layers: list[str]       # Conflicting layer IDs
    arc_types: list[str]    # Their arc type names
    values: list            # Their values


def detect_conflicts(stage: MerkleStage) -> list[Conflict]:
    """Find attributes where multiple layers disagree on the value.

    Two layers *conflict* on an attribute when they both define it
    but provide different values.  Layers that agree on the value
    are not reported as conflicting.
    """
    layers = stage.get_layers()

    # attr -> list of (value, layer_id, arc_type_name)
    attr_sources: dict[str, list[tuple[object, str, str]]] = defaultdict(list)

    for layer in layers:
        for attr, value in layer.data.items():
            attr_sources[attr].append((value, layer.layer_id, layer.arc_type.name))

    conflicts: list[Conflict] = []
    for attr, sources in attr_sources.items():
        # Check if there is more than one distinct value.
        distinct_values = set()
        for value, _, _ in sources:
            # Use repr for hashability of arbitrary values.
            distinct_values.add(repr(value))
        if len(distinct_values) > 1:
            conflicts.append(Conflict(
                attribute=attr,
                layers=[s[1] for s in sources],
                arc_types=[s[2] for s in sources],
                values=[s[0] for s in sources],
            ))

    return conflicts
