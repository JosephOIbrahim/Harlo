"""LIVRPS resolution for composition stages.

Strongest (LOCAL=1) wins per attribute.
When two layers share the same arc type, the later timestamp wins.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .layer import ArcType, Layer
from .stage import MerkleStage


@dataclass
class Resolution:
    """Result of resolving a MerkleStage."""
    merkle_root: str
    outcome: dict               # Resolved attribute -> value
    trace: list                 # Per-attribute resolution trace
    gvr_state: Optional[dict] = None  # Filled by Aletheia later


def resolve(stage: MerkleStage) -> Resolution:
    """Resolve a stage using LIVRPS priority.

    For each attribute present across all layers, the layer with the
    *strongest* arc type (lowest ArcType value) wins.  Ties on arc type
    are broken by *latest* timestamp.

    Returns a Resolution with the final outcome and a trace log.
    """
    layers = stage.get_layers()
    # best[attr] = (arc_type_value, timestamp, value, layer_id)
    best: dict[str, tuple[int, int, object, str]] = {}
    trace: list[dict] = []

    for layer in layers:
        for attr, value in layer.data.items():
            current = best.get(attr)
            # Lower arc_type value = stronger; on tie, higher timestamp wins.
            if current is None:
                best[attr] = (layer.arc_type.value, layer.timestamp, value, layer.layer_id)
                trace.append({
                    "attribute": attr,
                    "action": "set",
                    "layer_id": layer.layer_id,
                    "arc_type": layer.arc_type.name,
                    "value": value,
                })
            else:
                cur_arc, cur_ts, cur_val, cur_lid = current
                new_arc = layer.arc_type.value
                wins = False
                if new_arc < cur_arc:
                    wins = True
                elif new_arc == cur_arc and layer.timestamp > cur_ts:
                    wins = True

                if wins:
                    best[attr] = (new_arc, layer.timestamp, value, layer.layer_id)
                    trace.append({
                        "attribute": attr,
                        "action": "override",
                        "winner_layer": layer.layer_id,
                        "winner_arc": layer.arc_type.name,
                        "loser_layer": cur_lid,
                        "value": value,
                    })
                else:
                    trace.append({
                        "attribute": attr,
                        "action": "kept",
                        "kept_layer": cur_lid,
                        "rejected_layer": layer.layer_id,
                        "rejected_arc": layer.arc_type.name,
                    })

    outcome = {attr: entry[2] for attr, entry in best.items()}

    return Resolution(
        merkle_root=stage.get_merkle_root(),
        outcome=outcome,
        trace=trace,
    )
