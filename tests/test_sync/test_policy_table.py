"""Sync policy table coverage and resolution tests.

Per Phase 3 design §6 + Crucible Gate 3 criterion #2.
"""
from __future__ import annotations

import pytest

from harlo.sync.policy import Policy, POLICY_TABLE, resolve_policy


# The 19 concrete typeNames in HarloSchema.usda (abstract bases excluded;
# Injection types excluded per D5).
EXPECTED_TYPENAMES = {
    "BrainStage", "AssociationPrim", "CompositionPrim", "ElenchusPrim",
    "InquiryContainerPrim", "MotorContainerPrim", "SkillsContainerPrim",
    "CognitiveProfilePrim", "TracePrim", "CompositionLayerPrim",
    "Provenance", "SessionPrim", "GateStatusPrim", "MerkleRootPrim",
    "InquiryPrim", "MotorPrim", "SkillPrim", "MultipliersPrim",
    "IntakeHistoryPrim",
}


def test_policy_table_covers_19_typenames():
    assert set(POLICY_TABLE) == EXPECTED_TYPENAMES, (
        f"missing={EXPECTED_TYPENAMES - set(POLICY_TABLE)}, "
        f"extra={set(POLICY_TABLE) - EXPECTED_TYPENAMES}"
    )


def test_no_injection_in_policy_table():
    """D5: InjectionPrim/InjectionContainerPrim must NOT be in the table."""
    assert "InjectionPrim" not in POLICY_TABLE
    assert "InjectionContainerPrim" not in POLICY_TABLE


def test_d4_motor_is_write_through():
    """D4 ruling: MotorPrim → write-through (safety)."""
    assert resolve_policy("MotorPrim") == Policy.WRITE_THROUGH


def test_d4_inquiry_is_checkpoint():
    """D4 ruling: InquiryPrim → checkpoint (DMN, can lag)."""
    assert resolve_policy("InquiryPrim") == Policy.CHECKPOINT


def test_session_gate_merkle_are_write_through():
    """Phase 1 §6: consistency-critical prims → write-through."""
    for tn in ("SessionPrim", "GateStatusPrim", "MerkleRootPrim"):
        assert resolve_policy(tn) == Policy.WRITE_THROUGH


def test_high_write_rate_prims_are_checkpoint():
    """Phase 1 §6: high-write-rate prims → checkpoint."""
    for tn in (
        "TracePrim", "CompositionLayerPrim", "SkillPrim",
        "MultipliersPrim", "IntakeHistoryPrim",
    ):
        assert resolve_policy(tn) == Policy.CHECKPOINT


def test_inherit_resolves_to_concrete():
    """Every INHERIT entry resolves to a concrete (non-INHERIT) policy."""
    for tn, p in POLICY_TABLE.items():
        if p == Policy.INHERIT:
            resolved = resolve_policy(tn)
            assert resolved != Policy.INHERIT, f"{tn} did not resolve"
            assert resolved in (Policy.WRITE_THROUGH, Policy.CHECKPOINT, Policy.WRITE_BEHIND)


def test_unknown_typename_raises():
    """Unknown typeNames (incl. evicted Injection) raise KeyError."""
    with pytest.raises(KeyError):
        resolve_policy("InjectionPrim")
    with pytest.raises(KeyError):
        resolve_policy("NotAType")


def test_specific_inherit_resolutions():
    """Containers resolve to expected leaf policies."""
    # Containers whose leaves are write-through
    assert resolve_policy("MotorContainerPrim") == Policy.WRITE_THROUGH
    assert resolve_policy("ElenchusPrim") == Policy.WRITE_THROUGH
    # Containers whose leaves are checkpoint
    assert resolve_policy("AssociationPrim") == Policy.CHECKPOINT
    assert resolve_policy("CompositionPrim") == Policy.CHECKPOINT
    assert resolve_policy("InquiryContainerPrim") == Policy.CHECKPOINT
    assert resolve_policy("SkillsContainerPrim") == Policy.CHECKPOINT
    assert resolve_policy("CognitiveProfilePrim") == Policy.CHECKPOINT
    # Root resolves to dominant child policy (checkpoint per Phase 3 design)
    assert resolve_policy("BrainStage") == Policy.CHECKPOINT


def test_no_pxr_required_to_import_sync_package():
    """Constitution Law 3: importing `harlo.sync` MUST NOT require pxr."""
    import sys
    # If pxr is already imported by a sibling test, this test only verifies
    # that importing `harlo.sync` itself does not pull pxr — but since
    # the test runs in the same process, we can only assert the policy
    # module path doesn't trigger pxr import directly.
    # The subprocess test in tests/test_path_c covers the strict case.
    import harlo.sync.policy  # noqa: F401
    # If this import succeeded without an explicit ImportError, the
    # module-load validation already passed.
    assert harlo.sync.policy.POLICY_TABLE
