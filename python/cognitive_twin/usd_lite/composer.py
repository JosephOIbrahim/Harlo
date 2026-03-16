"""LIVRPS composition engine with permanent-prim handling.

Composes multiple opinion layers into a resolved value using USD-Lite
precedence rules.  Generalises the existing ``composition/resolver.py``
to handle permanent prims (Amygdala reflexes).

Resolution rules:
  1. Per-attribute: each attribute resolved independently.
  2. Arc type priority: lower ``ArcType`` value wins.
  3. Timestamp tie-breaking: same arc type -> later timestamp wins.
  4. Permanent override: ``permanent=True`` always wins over non-permanent.
     Among multiple permanents, latest timestamp wins.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .prims import CompositionLayerPrim


@dataclass
class CompositionResult:
    """Result of LIVRPS composition."""
    outcome: dict[str, object] = field(default_factory=dict)
    trace: list[dict] = field(default_factory=list)
    winning_layers: dict[str, str] = field(default_factory=dict)


def compose(layers: list[CompositionLayerPrim]) -> CompositionResult:
    """Resolve a list of composition layers using LIVRPS precedence.

    Permanent prims override normal LIVRPS recency rules.
    Returns the resolved outcome with an audit trace.
    """
    # best[attr] = (permanent, arc_type_value, timestamp, value, layer_id)
    best: dict[str, tuple[bool, int, float, object, str]] = {}
    trace: list[dict] = []

    for layer in layers:
        ts = layer.timestamp.timestamp()  # Convert datetime to float for comparison
        for attr, value in layer.opinion.items():
            current = best.get(attr)

            if current is None:
                best[attr] = (layer.permanent, layer.arc_type.value, ts, value, layer.layer_id)
                trace.append({
                    "attribute": attr,
                    "action": "set",
                    "layer_id": layer.layer_id,
                    "arc_type": layer.arc_type.name,
                    "permanent": layer.permanent,
                    "value": value,
                })
                continue

            cur_perm, cur_arc, cur_ts, cur_val, cur_lid = current
            wins = False
            reason = ""

            if layer.permanent and not cur_perm:
                wins = True
                reason = "permanent_override"
            elif layer.permanent and cur_perm:
                if ts > cur_ts:
                    wins = True
                    reason = "permanent_recency"
            elif not layer.permanent and cur_perm:
                wins = False
                reason = "blocked_by_permanent"
            else:
                # Normal LIVRPS
                if layer.arc_type.value < cur_arc:
                    wins = True
                    reason = "stronger_arc"
                elif layer.arc_type.value == cur_arc and ts > cur_ts:
                    wins = True
                    reason = "same_arc_recency"

            if wins:
                best[attr] = (layer.permanent, layer.arc_type.value, ts, value, layer.layer_id)
                trace.append({
                    "attribute": attr,
                    "action": "override",
                    "reason": reason,
                    "winner_layer": layer.layer_id,
                    "winner_arc": layer.arc_type.name,
                    "loser_layer": cur_lid,
                    "permanent": layer.permanent,
                    "value": value,
                })
            else:
                trace.append({
                    "attribute": attr,
                    "action": "kept",
                    "reason": reason or "weaker",
                    "kept_layer": cur_lid,
                    "rejected_layer": layer.layer_id,
                    "rejected_arc": layer.arc_type.name,
                })

    outcome = {attr: entry[3] for attr, entry in best.items()}
    winning_layers = {attr: entry[4] for attr, entry in best.items()}

    return CompositionResult(
        outcome=outcome,
        trace=trace,
        winning_layers=winning_layers,
    )
