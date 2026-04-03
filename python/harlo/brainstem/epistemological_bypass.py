"""Epistemological bypass -- Safeguard S2.

Inquiry outputs bypass Elenchus truth-checking (tone only).
Self-reported data consumed by inquiry -> bypass.
Self-reported data consumed by composition -> standard verification.
This bypass is DIRECTIONAL.

Rule 20: PERCEPTION GAP TRACES.
Rule 33: BLIND SPOT ACCEPTANCE.

Absorbed from bridge/ in Phase 4.
"""

from __future__ import annotations

import time


# Source types that qualify for epistemological bypass
_INQUIRY_SOURCES = frozenset({"inquiry", "dmn_inquiry", "self_inquiry"})
_SELF_REPORTED_TAGS = frozenset({"self_reported", "subjective", "introspective"})


def should_bypass_elenchus(
    source: str,
    tags: list,
    consumer: str,
) -> bool:
    """Determine if Elenchus truth-checking should be bypassed.

    Safeguard S2 (DIRECTIONAL):
      - Inquiry outputs -> bypass truth check (tone only).
      - Self-reported consumed by inquiry -> bypass.
      - Self-reported consumed by composition -> standard verification.
    """
    source_lower = source.lower() if source else ""
    consumer_lower = consumer.lower() if consumer else ""
    tag_set = frozenset(t.lower() for t in tags) if tags else frozenset()

    if source_lower in _INQUIRY_SOURCES:
        return True

    if tag_set & _SELF_REPORTED_TAGS:
        if consumer_lower in _INQUIRY_SOURCES or consumer_lower == "inquiry":
            return True
        if consumer_lower in ("composition", "compose"):
            return False

    return False


def emit_perception_gap(
    self_reported: dict,
    finding: dict,
) -> dict:
    """Emit a perception_gap trace when Elenchus falsifies self_reported data.

    Rule 20: When Elenchus falsifies self_reported in Composition,
    emit perception_gap trace for DMN inquiry to process.
    """
    return {
        "type": "perception_gap",
        "timestamp": int(time.time()),
        "self_reported": self_reported,
        "elenchus_finding": finding,
        "status": "pending_inquiry",
        "tags": ["perception_gap", "self_reported_falsified"],
    }


def accept_blind_spot(perception_gap_trace: dict, reason: str = "") -> dict:
    """Tag a perception_gap as blind_spot_accepted (Rule 33)."""
    updated = dict(perception_gap_trace)
    tags = list(updated.get("tags", []))
    if "blind_spot_accepted" not in tags:
        tags.append("blind_spot_accepted")
    updated["tags"] = tags
    updated["status"] = "blind_spot_accepted"
    updated["blind_spot_accepted_at"] = int(time.time())
    if reason:
        updated["blind_spot_reason"] = reason
    return updated
