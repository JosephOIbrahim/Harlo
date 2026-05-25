"""Tests for the intake → composition Merkle layer bridge.

Verifies:
  - Three layers are produced with the expected ids.
  - Every layer carries `Provenance.INTAKE_CALIBRATED`.
  - Anchor annotations layer reaffirms structural 1.0 (Rule 7, Rule 10).
  - Coaching context layer includes apophenia delta within ±10% cap.
  - Hash is deterministic across two identical sessions.
"""

from __future__ import annotations

from harlo.intake.coaching_scaffold import scaffold
from harlo.intake.composition_bridge import to_layers
from harlo.intake.questionnaire import IntakeSession


def _completed_session() -> IntakeSession:
    return IntakeSession(
        current_index=6,
        answers={
            "q1_assoc": 0.7,
            "q2_detail": 0.4,
            "q3_attention": 0.6,
            "q4_stress": 0.3,
            "q5_assoc2": 0.65,
            "q6_detail2": 0.45,
        },
    )


def test_three_layers_produced() -> None:
    session = _completed_session()
    sc = scaffold(session)
    layers = to_layers(
        session,
        session_id="test-session",
        derived_multipliers={
            "surprise_threshold": 2.0,
            "reconstruction_threshold": 0.25,
            "hebbian_alpha": 0.012,
            "allostatic_threshold": 0.9,
            "detail_orientation": 0.45,
        },
        scaffold_out=sc,
    )
    ids = [l["layer_id"] for l in layers]
    assert ids == ["UserProfile", "InitialAnchorAnnotations", "CoachingContext"]


def test_every_layer_is_intake_calibrated() -> None:
    session = _completed_session()
    sc = scaffold(session)
    layers = to_layers(
        session,
        session_id="test-session",
        derived_multipliers={"surprise_threshold": 2.0},
        scaffold_out=sc,
    )
    for layer in layers:
        assert layer["provenance"]["source_type"] == "intake_calibrated"


def test_anchor_layer_affirms_structural_1_0() -> None:
    session = _completed_session()
    sc = scaffold(session)
    layers = to_layers(
        session,
        session_id="test-session",
        derived_multipliers={"surprise_threshold": 2.0},
        scaffold_out=sc,
    )
    anchor = next(l for l in layers if l["layer_id"] == "InitialAnchorAnnotations")
    assert anchor["content"]["anchors_structural_1_0"] is True


def test_apophenia_delta_within_cap() -> None:
    session = _completed_session()
    sc = scaffold(session)
    assert -0.10 <= sc.apophenia_baseline_delta <= 0.10


def test_intake_hash_is_deterministic() -> None:
    a = to_layers(
        _completed_session(),
        session_id="x",
        derived_multipliers={"surprise_threshold": 2.0},
        scaffold_out=scaffold(_completed_session()),
    )
    b = to_layers(
        _completed_session(),
        session_id="y",
        derived_multipliers={"surprise_threshold": 2.0},
        scaffold_out=scaffold(_completed_session()),
    )
    assert a[0]["provenance"]["event_hash"] == b[0]["provenance"]["event_hash"]
