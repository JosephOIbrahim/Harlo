"""Gate 4e: Multiplier derivation — continuous scoring, deterministic."""

from __future__ import annotations

import math

from harlo.intake.multipliers import build_cognitive_profile, derive_multipliers
from harlo.intake.questionnaire import IntakeSession


class TestDeriveMultipliers:
    """Continuous [0.0, 1.0] scoring with deterministic linear interpolation."""

    def test_default_midpoint(self) -> None:
        """All 0.5 scores → midpoint multipliers."""
        session = IntakeSession(
            current_index=6,
            answers={
                "q1_assoc": 0.5,
                "q2_detail": 0.5,
                "q3_attention": 0.5,
                "q4_stress": 0.5,
                "q5_assoc2": 0.5,
                "q6_detail2": 0.5,
            },
            completed=True,
        )
        m = derive_multipliers(session)
        assert math.isclose(m.surprise_threshold, 2.0, rel_tol=1e-6)
        assert math.isclose(m.detail_orientation, 0.5, rel_tol=1e-6)
        assert math.isclose(m.hebbian_alpha, 0.0125, rel_tol=1e-6)

    def test_low_scores(self) -> None:
        """All 0.0 scores → base multipliers."""
        session = IntakeSession(
            current_index=6,
            answers={
                "q1_assoc": 0.0,
                "q2_detail": 0.0,
                "q3_attention": 0.0,
                "q4_stress": 0.0,
                "q5_assoc2": 0.0,
                "q6_detail2": 0.0,
            },
            completed=True,
        )
        m = derive_multipliers(session)
        assert math.isclose(m.surprise_threshold, 1.5, rel_tol=1e-6)
        assert math.isclose(m.detail_orientation, 0.0, rel_tol=1e-6)
        assert math.isclose(m.hebbian_alpha, 0.005, rel_tol=1e-6)
        assert math.isclose(m.allostatic_threshold, 0.5, rel_tol=1e-6)

    def test_high_scores(self) -> None:
        """All 1.0 scores → max multipliers."""
        session = IntakeSession(
            current_index=6,
            answers={
                "q1_assoc": 1.0,
                "q2_detail": 1.0,
                "q3_attention": 1.0,
                "q4_stress": 1.0,
                "q5_assoc2": 1.0,
                "q6_detail2": 1.0,
            },
            completed=True,
        )
        m = derive_multipliers(session)
        assert math.isclose(m.surprise_threshold, 2.5, rel_tol=1e-6)
        assert math.isclose(m.detail_orientation, 1.0, rel_tol=1e-6)
        assert math.isclose(m.hebbian_alpha, 0.02, rel_tol=1e-6)
        assert math.isclose(m.allostatic_threshold, 1.5, rel_tol=1e-6)

    def test_deterministic(self) -> None:
        """Same answers → same multipliers."""
        session = IntakeSession(
            current_index=6,
            answers={
                "q1_assoc": 0.3,
                "q2_detail": 0.7,
                "q3_attention": 0.4,
                "q4_stress": 0.6,
                "q5_assoc2": 0.8,
                "q6_detail2": 0.2,
            },
            completed=True,
        )
        m1 = derive_multipliers(session)
        m2 = derive_multipliers(session)
        assert m1.surprise_threshold == m2.surprise_threshold
        assert m1.reconstruction_threshold == m2.reconstruction_threshold
        assert m1.hebbian_alpha == m2.hebbian_alpha
        assert m1.allostatic_threshold == m2.allostatic_threshold
        assert m1.detail_orientation == m2.detail_orientation

    def test_linear_interpolation(self) -> None:
        """multiplier = base + (score * range) verified."""
        session = IntakeSession(
            current_index=6,
            answers={
                "q1_assoc": 0.4,
                "q5_assoc2": 0.6,
                "q2_detail": 0.5,
                "q6_detail2": 0.5,
                "q3_attention": 0.0,
                "q4_stress": 1.0,
            },
            completed=True,
        )
        m = derive_multipliers(session)
        # Associativity avg = 0.5 → surprise = 1.5 + 0.5*1.0 = 2.0
        assert math.isclose(m.surprise_threshold, 2.0, rel_tol=1e-6)
        # Stress = 1.0 → allostatic = 0.5 + 1.0*1.0 = 1.5
        assert math.isclose(m.allostatic_threshold, 1.5, rel_tol=1e-6)
        # Attention = 0.0 → hebbian = 0.005 + 0.0*0.015 = 0.005
        assert math.isclose(m.hebbian_alpha, 0.005, rel_tol=1e-6)


class TestBuildCognitiveProfile:
    """Profile construction from intake session."""

    def test_builds_profile(self) -> None:
        session = IntakeSession(
            current_index=6,
            answers={
                "q1_assoc": 0.5,
                "q2_detail": 0.5,
                "q3_attention": 0.5,
                "q4_stress": 0.5,
                "q5_assoc2": 0.5,
                "q6_detail2": 0.5,
            },
            completed=True,
        )
        profile = build_cognitive_profile(session)
        assert profile.multipliers.surprise_threshold > 0
        assert profile.intake_history.last_intake is not None
        assert profile.intake_history.intake_version == "1.0"

    def test_rerun_updates(self) -> None:
        """Re-running intake returns a fresh profile, not append."""
        session = IntakeSession(
            current_index=6,
            answers={"q1_assoc": 0.3, "q2_detail": 0.7, "q3_attention": 0.5,
                     "q4_stress": 0.5, "q5_assoc2": 0.5, "q6_detail2": 0.5},
            completed=True,
        )
        p1 = build_cognitive_profile(session, intake_version="1.0")
        p2 = build_cognitive_profile(session, intake_version="2.0")
        assert p2.intake_history.intake_version == "2.0"
