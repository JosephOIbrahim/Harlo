"""Structured provenance stamping for composition layers.

Phase 3: Every composition layer gets a Provenance dataclass with
source_type, origin_timestamp, event_hash, and session_id.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional

from ..usd_lite.prims import (
    CompositionLayerPrim,
    Provenance,
    SourceType,
)


def stamp_provenance(
    layer: CompositionLayerPrim,
    source_type: SourceType,
    session_id: str,
    event_data: Optional[str] = None,
) -> CompositionLayerPrim:
    """Attach structured provenance to a composition layer prim.

    Creates a deterministic event_hash from the layer_id + timestamp + event_data.
    Returns a new CompositionLayerPrim with provenance set.
    """
    hash_input = f"{layer.layer_id}:{layer.timestamp.isoformat()}:{event_data or ''}"
    event_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

    provenance = Provenance(
        source_type=source_type,
        origin_timestamp=layer.timestamp,
        event_hash=event_hash,
        session_id=session_id,
    )

    return CompositionLayerPrim(
        layer_id=layer.layer_id,
        arc_type=layer.arc_type,
        opinion=layer.opinion,
        timestamp=layer.timestamp,
        provenance=provenance,
        permanent=layer.permanent,
    )


def migrate_legacy_provenance(
    layer: CompositionLayerPrim,
    session_id: str = "legacy",
) -> CompositionLayerPrim:
    """Add SYSTEM_INFERRED provenance to a legacy layer without provenance.

    Used during v6→v7 migration. Only stamps layers that don't already
    have provenance.
    """
    if layer.provenance is not None:
        return layer
    return stamp_provenance(
        layer=layer,
        source_type=SourceType.SYSTEM_INFERRED,
        session_id=session_id,
        event_data="v6_migration",
    )


def make_event_hash(layer_id: str, timestamp: datetime, event_data: str = "") -> str:
    """Compute a deterministic event hash."""
    hash_input = f"{layer_id}:{timestamp.isoformat()}:{event_data}"
    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
