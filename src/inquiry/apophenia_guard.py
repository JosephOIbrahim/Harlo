"""Apophenia Guard — S1: Evidence-gated inquiry generation.

Min evidence threshold per depth (5/8/15/25).
Alternative hypothesis required for every inquiry.
Prevents the Twin from hallucinating patterns in noise.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .types import EVIDENCE_THRESHOLDS


@dataclass
class EvidenceBundle:
    """A set of observations supporting an inquiry hypothesis."""
    observations: list[str] = field(default_factory=list)
    hypothesis: str = ""
    alt_hypothesis: str = ""
    depth: int = 1

    @property
    def count(self) -> int:
        return len(self.observations)

    @property
    def threshold(self) -> int:
        return EVIDENCE_THRESHOLDS.get(self.depth, EVIDENCE_THRESHOLDS[4])


@dataclass
class GuardResult:
    """Result of apophenia guard evaluation."""
    passed: bool
    reason: str
    evidence_count: int
    required_count: int
    depth: int


def evaluate(bundle: EvidenceBundle) -> GuardResult:
    """Evaluate whether an evidence bundle passes the apophenia guard.

    S1: Requires min evidence per depth AND an alternative hypothesis.
    """
    required = bundle.threshold

    if not bundle.hypothesis:
        return GuardResult(
            passed=False,
            reason="no_hypothesis",
            evidence_count=bundle.count,
            required_count=required,
            depth=bundle.depth,
        )

    if not bundle.alt_hypothesis:
        return GuardResult(
            passed=False,
            reason="no_alt_hypothesis",
            evidence_count=bundle.count,
            required_count=required,
            depth=bundle.depth,
        )

    if bundle.count < required:
        return GuardResult(
            passed=False,
            reason="insufficient_evidence",
            evidence_count=bundle.count,
            required_count=required,
            depth=bundle.depth,
        )

    return GuardResult(
        passed=True,
        reason="passed",
        evidence_count=bundle.count,
        required_count=required,
        depth=bundle.depth,
    )
