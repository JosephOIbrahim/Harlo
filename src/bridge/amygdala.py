"""Amygdala — 1-shot permanent reflex for SAFETY/CONSENT (Rule 7).

When a resolution involves safety or consent anchors, it becomes a
permanent reflex immediately, skipping the full GVR cycle.
"""

from __future__ import annotations

import hashlib
import json
import time


# ------------------------------------------------------------------
# Anchor keyword sets
# ------------------------------------------------------------------

SAFETY_KEYWORDS = frozenset({
    "safety", "harm", "danger", "dangerous", "hazard", "hazardous",
    "risk", "threat", "injury", "lethal", "fatal", "toxic",
    "poison", "weapon", "violence", "abuse", "self-harm",
    "suicide", "emergency", "critical", "warning", "alert",
    "protect", "protection", "vulnerable", "minor", "child",
})

CONSENT_KEYWORDS = frozenset({
    "consent", "permission", "authorize", "authorise", "authorization",
    "approval", "approve", "deny", "denied", "refuse", "refused",
    "opt-in", "opt-out", "agree", "agreement", "decline",
    "revoke", "revocation", "boundary", "boundaries", "privacy",
    "confidential", "personal", "sensitive", "disclosure",
})


# ------------------------------------------------------------------
# Detection
# ------------------------------------------------------------------

def _extract_text(resolution: dict) -> str:
    """Extract searchable text from a resolution dict."""
    parts: list[str] = []

    outcome = resolution.get("outcome", {})
    if isinstance(outcome, dict):
        for v in outcome.values():
            parts.append(str(v))
    elif isinstance(outcome, str):
        parts.append(outcome)

    for tag in resolution.get("tags", []):
        parts.append(str(tag))

    trace = resolution.get("trace", [])
    if isinstance(trace, list):
        for entry in trace:
            if isinstance(entry, dict):
                parts.append(str(entry.get("attribute", "")))
                parts.append(str(entry.get("value", "")))

    return " ".join(parts).lower()


def is_amygdala_trigger(resolution: dict) -> bool:
    """Check if resolution involves SAFETY or CONSENT anchors.

    If True, the resolution should become a 1-shot permanent reflex
    and skip full GVR verification (Rule 7).
    """
    # Check explicit anchor tags first
    anchors = resolution.get("anchors", [])
    if isinstance(anchors, str):
        anchors = [anchors]
    for anchor in anchors:
        if anchor.upper() in ("SAFETY", "CONSENT"):
            return True

    # Fall back to keyword detection in content
    text = _extract_text(resolution)

    for kw in SAFETY_KEYWORDS:
        if kw in text:
            return True

    for kw in CONSENT_KEYWORDS:
        if kw in text:
            return True

    return False


# ------------------------------------------------------------------
# Reflex creation
# ------------------------------------------------------------------

def create_amygdala_reflex(resolution: dict) -> dict:
    """Create a permanent reflex for a safety/consent resolution.

    Rule 7: These are 1-shot, permanent, and skip GVR.
    The reflex is tagged with its trigger type (safety/consent/both).
    """
    text = _extract_text(resolution)

    triggers: list[str] = []
    matched_safety = [kw for kw in SAFETY_KEYWORDS if kw in text]
    matched_consent = [kw for kw in CONSENT_KEYWORDS if kw in text]

    if matched_safety:
        triggers.append("SAFETY")
    if matched_consent:
        triggers.append("CONSENT")

    # Deterministic hash for the reflex
    canonical = json.dumps(resolution.get("outcome", {}), sort_keys=True)
    reflex_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return {
        "pattern_hash": f"amygdala_{reflex_hash[:32]}",
        "reflex_hash": reflex_hash,
        "type": "amygdala_permanent",
        "triggers": triggers,
        "matched_keywords": {
            "safety": sorted(matched_safety),
            "consent": sorted(matched_consent),
        },
        "response": resolution.get("outcome", {}),
        "outcome": resolution.get("outcome", {}),
        "merkle_root": resolution.get("merkle_root", ""),
        "verification_state": "amygdala_bypass",
        "is_permanent": True,
        "compiled": True,
        "hit_count": 0,
        "success_count": 0,
        "created_at": int(time.time()),
    }
