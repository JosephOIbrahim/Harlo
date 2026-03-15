"""Epistemological bypass -- Safeguard S2.

Inquiry outputs bypass Aletheia truth-checking (tone only).
Self-reported data consumed by inquiry -> bypass.
Self-reported data consumed by composition -> standard verification.
This bypass is DIRECTIONAL.

Rule 20: PERCEPTION GAP TRACES. When Aletheia falsifies self_reported
in Composition, emit perception_gap trace for DMN inquiry.

Rule 33: BLIND SPOT ACCEPTANCE. If user rejects perception_gap inquiry,
tag blind_spot_accepted.
"""

from __future__ import annotations

import time


# Source types that qualify for epistemological bypass
_INQUIRY_SOURCES = frozenset({"inquiry", "dmn_inquiry", "self_inquiry"})
_SELF_REPORTED_TAGS = frozenset({"self_reported", "subjective", "introspective"})


def should_bypass_aletheia(
    source: str,
    tags: list,
    consumer: str,
) -> bool:
    """Determine if Aletheia truth-checking should be bypassed.

    Safeguard S2 (DIRECTIONAL):
      - Inquiry outputs -> bypass truth check (tone only).
      - Self-reported consumed by inquiry -> bypass.
      - Self-reported consumed by composition -> standard verification.

    Args:
        source: The originating subsystem (e.g. "inquiry", "composition").
        tags: Tags on the data (e.g. ["self_reported"]).
        consumer: The subsystem consuming this data.

    Returns:
        True if Aletheia truth-checking should be bypassed.
    """
    source_lower = source.lower() if source else ""
    consumer_lower = consumer.lower() if consumer else ""
    tag_set = frozenset(t.lower() for t in tags) if tags else frozenset()

    # Inquiry outputs always bypass truth-check
    if source_lower in _INQUIRY_SOURCES:
        return True

    # Self-reported consumed by inquiry -> bypass
    if tag_set & _SELF_REPORTED_TAGS:
        if consumer_lower in _INQUIRY_SOURCES or consumer_lower == "inquiry":
            return True
        # Self-reported consumed by composition -> NO bypass (standard verification)
        if consumer_lower in ("composition", "compose"):
            return False

    return False


def emit_perception_gap(
    self_reported: dict,
    finding: dict,
) -> dict:
    """Emit a perception_gap trace when Aletheia falsifies self_reported data.

    Rule 20: When Aletheia falsifies self_reported in Composition,
    emit perception_gap trace for DMN inquiry to process.

    Args:
        self_reported: The user's self-reported data that was falsified.
        finding: Aletheia's finding that contradicts the self-report.

    Returns:
        A perception_gap trace dict suitable for DMN inquiry.
    """
    return {
        "type": "perception_gap",
        "timestamp": int(time.time()),
        "self_reported": self_reported,
        "aletheia_finding": finding,
        "status": "pending_inquiry",
        "tags": ["perception_gap", "self_reported_falsified"],
    }


def accept_blind_spot(perception_gap_trace: dict, reason: str = "") -> dict:
    """Tag a perception_gap as blind_spot_accepted (Rule 33).

    Called when the user rejects a perception_gap inquiry result.
    The system respects the user's autonomy but records the rejection.

    Args:
        perception_gap_trace: The original perception_gap trace.
        reason: Optional reason for rejection.

    Returns:
        Updated trace with blind_spot_accepted tag.
    """
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
