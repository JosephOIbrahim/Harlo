"""Coaching scaffold derived from intake responses.

Pure function. Maps the user's `IntakeSession` into:

  - A set of inquiry *templates* (NOT live inquiries — S1 requires
    5/8/15/25 independent observations before any inquiry can
    surface).
  - Bounded adjustments to the DMN's apophenia baseline (cap ±10%).
  - Coaching voice hints consumed by `project_coach()` when it
    builds the system prompt.
  - Read-only anchor annotations. Anchors stay structural 1.0
    (Rule 7, Rule 10) — annotations are framing hints, never gains.

This module touches no SQLite, no stages, no traces. It is a data
transformation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .questionnaire import IntakeSession

# Apophenia adjustments are capped at ±10% of baseline. Strong intake
# signals nudge but never override the DMN's structural minimum.
_APOPHENIA_CAP = 0.10


@dataclass(frozen=True)
class InquiryTemplate:
    """A template the DMN MAY instantiate later, once it has enough
    independent observations to satisfy S1."""

    dimension: str
    framing: str
    minimum_observations: int  # The S1 floor for this depth.


@dataclass(frozen=True)
class CoachingVoice:
    """Hints for `project_coach()` system prompt assembly."""

    directness: float  # 0.0 (soft) → 1.0 (direct)
    warmth: float      # 0.0 (terse) → 1.0 (warm)
    rupture_tolerance: Literal["low", "medium", "high"]


@dataclass(frozen=True)
class CoachingScaffold:
    """The full output handed to the composition bridge."""

    inquiry_templates: tuple[InquiryTemplate, ...]
    apophenia_baseline_delta: float
    voice: CoachingVoice
    anchor_annotations: dict[str, str] = field(default_factory=dict)


def _dimension_average(session: IntakeSession, dimension: str) -> float | None:
    """Mean of scored answers for one dimension, or None if no data."""
    from .multipliers import _QUESTION_DIMENSIONS
    values = [
        score
        for qid, score in session.answers.items()
        if _QUESTION_DIMENSIONS.get(qid) == dimension
    ]
    if not values:
        return None
    return sum(values) / len(values)


def _classify_voice(session: IntakeSession) -> CoachingVoice:
    detail = _dimension_average(session, "detail") or 0.5
    stress = _dimension_average(session, "stress") or 0.5
    attention = _dimension_average(session, "attention") or 0.5

    directness = max(0.0, min(1.0, detail))
    warmth = max(0.0, min(1.0, 1.0 - 0.6 * stress))

    if stress >= 0.7:
        tolerance: Literal["low", "medium", "high"] = "low"
    elif attention >= 0.7:
        tolerance = "high"
    else:
        tolerance = "medium"

    return CoachingVoice(
        directness=directness,
        warmth=warmth,
        rupture_tolerance=tolerance,
    )


def _apophenia_delta(session: IntakeSession) -> float:
    """A bounded nudge: highly stressed users get a stricter
    apophenia floor (lower delta → more evidence required); highly
    associative users get a slightly looser one. Capped at ±10%.
    """
    stress = _dimension_average(session, "stress") or 0.5
    assoc = _dimension_average(session, "associativity") or 0.5
    raw = 0.5 * (assoc - 0.5) - 0.5 * (stress - 0.5)
    delta = max(-_APOPHENIA_CAP, min(_APOPHENIA_CAP, raw * _APOPHENIA_CAP * 2))
    return delta


def _build_templates(session: IntakeSession) -> tuple[InquiryTemplate, ...]:
    templates: list[InquiryTemplate] = []
    for dim in ("associativity", "detail", "attention", "stress"):
        avg = _dimension_average(session, dim)
        if avg is None:
            continue
        templates.append(
            InquiryTemplate(
                dimension=dim,
                framing=f"track-{dim}-coherence",
                minimum_observations=5,
            )
        )
    return tuple(templates)


def scaffold(session: IntakeSession) -> CoachingScaffold:
    """Build a `CoachingScaffold` from a completed intake session.

    Does not surface any live inquiry. The DMN consumes the templates
    later, when S1's evidence floor is satisfied.
    """
    return CoachingScaffold(
        inquiry_templates=_build_templates(session),
        apophenia_baseline_delta=_apophenia_delta(session),
        voice=_classify_voice(session),
        anchor_annotations={},  # Reserved; populated only via explicit user input.
    )


__all__ = [
    "CoachingScaffold",
    "CoachingVoice",
    "InquiryTemplate",
    "scaffold",
]
