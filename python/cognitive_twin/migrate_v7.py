"""v6 → v7 migration script.

Bootstraps /Skills from legacy trace timestamps in SQLite.
One-time full scan acceptable; subsequent runs are incremental.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .skills.observer import ObserverCursor, initial_cursor, observe_traces
from .usd_lite.prims import (
    AssociationPrim,
    SkillsContainerPrim,
    TracePrim,
)


def migrate_skills_from_traces(
    traces: dict[str, TracePrim],
    existing_skills: Optional[SkillsContainerPrim] = None,
) -> tuple[SkillsContainerPrim, ObserverCursor]:
    """Bootstrap /Skills from legacy trace data.

    Performs a full scan of all traces (acceptable as one-time migration cost).
    Returns populated SkillsContainerPrim and cursor positioned at latest trace.
    """
    if existing_skills is None:
        existing_skills = SkillsContainerPrim()

    cursor = initial_cursor()
    return observe_traces(traces, existing_skills, cursor)


def create_legacy_traces(trace_records: list[dict]) -> dict[str, TracePrim]:
    """Convert legacy SQLite trace records to TracePrims for migration.

    Each record should have: id, message, initial_strength, created_at, last_accessed.
    SDR is set to zeros (original bytes not needed for skill building).
    """
    traces: dict[str, TracePrim] = {}
    for record in trace_records:
        tid = record.get("id", record.get("trace_id", ""))
        created = record.get("created_at", 0)
        accessed = record.get("last_accessed", created)
        strength = record.get("initial_strength", record.get("strength", 0.5))

        # Convert unix timestamps to datetime
        if isinstance(accessed, (int, float)):
            last_dt = datetime.fromtimestamp(accessed, tz=timezone.utc)
        else:
            last_dt = accessed

        traces[tid] = TracePrim(
            trace_id=tid,
            sdr=[0] * 2048,
            content_hash=record.get("content_hash", f"legacy_{tid}"),
            strength=strength,
            last_accessed=last_dt,
        )
    return traces
