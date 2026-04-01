"""Intent preservation check (Rule 14).

The output must answer the *original* intent. Also checks for
profile-driven bias that could distort the answer.

Absorbed from bridge/ in Phase 4.
"""

from __future__ import annotations

from typing import Optional

from ..elenchus.intent import check_intent_alignment, extract_intent


def check_intent_preserved(
    intent: str,
    resolution: dict,
    profile=None,
) -> dict:
    """Check if the resolution output answers the original intent.

    Rule 14: INTENT PRESERVATION.

    Args:
        intent: The original user intent string.
        resolution: The resolution dict (must contain 'outcome').
        profile: Optional Profile object; if present, check for bias.

    Returns:
        dict with keys:
          - preserved (bool): True if output addresses original intent.
          - original_intent: The cleaned intent.
          - drift_reason: Why intent was not preserved (if applicable).
          - bias_warning: Profile bias warning (if applicable).
    """
    cleaned_intent = extract_intent(intent) if intent else ""

    result: dict = {
        "preserved": False,
        "original_intent": cleaned_intent,
        "drift_reason": None,
        "bias_warning": None,
    }

    if not cleaned_intent:
        result["drift_reason"] = "Empty intent -- nothing to preserve"
        return result

    # Flatten the resolution outcome to text
    outcome = resolution.get("outcome", {})
    if isinstance(outcome, dict):
        output_text = " ".join(str(v) for v in outcome.values())
    else:
        output_text = str(outcome)

    if not output_text.strip():
        result["drift_reason"] = "Empty resolution output"
        return result

    # Use Elenchus's alignment checker
    aligned = check_intent_alignment(cleaned_intent, output_text)
    result["preserved"] = aligned

    if not aligned:
        result["drift_reason"] = (
            "Resolution output does not sufficiently address "
            "the original intent"
        )

    # Profile bias check
    if profile is not None:
        bias = _check_profile_bias(cleaned_intent, output_text, profile)
        if bias:
            result["bias_warning"] = bias

    return result


def _check_profile_bias(intent: str, output: str, profile) -> Optional[str]:
    """Detect if the profile's modulation parameters may have biased the output."""
    anchors = getattr(profile, "anchors", [])
    if not anchors:
        return None

    intent_lower = intent.lower()
    output_lower = output.lower()

    anchor_in_output = [a for a in anchors if a.lower() in output_lower]
    anchor_in_intent = [a for a in anchors if a.lower() in intent_lower]

    if anchor_in_output and not anchor_in_intent:
        ratio = len(anchor_in_output) / max(len(output.split()), 1)
        if ratio > 0.1:
            return (
                f"Profile anchors {anchor_in_output} appear in output "
                f"but not in intent -- possible profile bias"
            )

    return None
