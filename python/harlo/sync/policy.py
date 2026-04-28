"""Path C sync policy table.

Per-prim sync policy declarations. Single source of truth for which
strategy each of the 19 concrete typeNames uses.

Authority: Phase 1 design §6 (defaults) + D4 (orphan-prim rulings) +
Phase 3 sync layer design §3 (final table). InjectionPrim and
InjectionContainerPrim are NOT in this table per D5 (evicted from
schema).

Module-load-time validation enforces that every concrete typeName has
an entry and every INHERIT entry resolves to a non-INHERIT policy.
"""
from __future__ import annotations

from enum import Enum


class Policy(Enum):
    """Sync strategy classification."""
    WRITE_THROUGH = "write_through"
    CHECKPOINT = "checkpoint"
    WRITE_BEHIND = "write_behind"
    INHERIT = "inherit"


# Single source of truth — keys are the 19 concrete typeNames in HarloSchema.usda.
# Abstract bases (HarloPrim, HarloContainer) and evicted Injection types
# are deliberately omitted.
POLICY_TABLE: dict[str, Policy] = {
    # Containers (resolve via INHERIT)
    "BrainStage": Policy.INHERIT,
    "AssociationPrim": Policy.INHERIT,
    "CompositionPrim": Policy.INHERIT,
    "ElenchusPrim": Policy.INHERIT,
    "InquiryContainerPrim": Policy.INHERIT,
    "MotorContainerPrim": Policy.INHERIT,
    "SkillsContainerPrim": Policy.INHERIT,
    "CognitiveProfilePrim": Policy.INHERIT,

    # Concrete typed leaves (Phase 1 §6 + D4)
    "TracePrim": Policy.CHECKPOINT,
    "CompositionLayerPrim": Policy.CHECKPOINT,
    "Provenance": Policy.CHECKPOINT,            # apiSchema; inherits host
    "SessionPrim": Policy.WRITE_THROUGH,
    "GateStatusPrim": Policy.WRITE_THROUGH,
    "MerkleRootPrim": Policy.WRITE_THROUGH,
    "InquiryPrim": Policy.CHECKPOINT,           # D4
    "MotorPrim": Policy.WRITE_THROUGH,          # D4 (safety)
    "SkillPrim": Policy.CHECKPOINT,
    "MultipliersPrim": Policy.CHECKPOINT,
    "IntakeHistoryPrim": Policy.CHECKPOINT,
}


# Container → leaf resolution map for INHERIT policies. The leaf
# determines the effective strategy.
_INHERIT_RESOLUTION: dict[str, str] = {
    "AssociationPrim": "TracePrim",
    "CompositionPrim": "CompositionLayerPrim",
    "ElenchusPrim": "GateStatusPrim",          # GateStatusPrim/MerkleRootPrim both write-through; pick either
    "InquiryContainerPrim": "InquiryPrim",
    "MotorContainerPrim": "MotorPrim",
    "SkillsContainerPrim": "SkillPrim",
    "CognitiveProfilePrim": "MultipliersPrim",  # Multipliers/IntakeHistory both checkpoint
    "BrainStage": "TracePrim",                  # Root inherits the dominant child policy (checkpoint).
}


def resolve_policy(typename: str) -> Policy:
    """Resolve a typeName to its effective Policy, walking INHERIT chains.

    Raises KeyError for unknown typeNames (incl. the evicted Injection
    types). Raises ValueError if INHERIT chains do not terminate (which
    shouldn't happen given the module-load validation).

    Bounded by the number of typeNames in POLICY_TABLE (Rule 1: no
    unbounded loops). The chain length cannot exceed table size in any
    valid configuration.
    """
    seen: set[str] = set()
    cur = typename
    for _ in range(len(POLICY_TABLE) + 1):
        if cur in seen:
            raise ValueError(f"INHERIT cycle starting at {typename!r}: {seen | {cur}}")
        seen.add(cur)
        policy = POLICY_TABLE[cur]
        if policy != Policy.INHERIT:
            return policy
        cur = _INHERIT_RESOLUTION[cur]
    raise ValueError(f"INHERIT chain exceeded table size starting at {typename!r}")


def _validate_table_completeness() -> None:
    """Module-load-time check: every entry resolves and the table covers
    the 19 concrete typeNames in HarloSchema.usda."""
    expected = {
        "BrainStage", "AssociationPrim", "CompositionPrim", "ElenchusPrim",
        "InquiryContainerPrim", "MotorContainerPrim", "SkillsContainerPrim",
        "CognitiveProfilePrim", "TracePrim", "CompositionLayerPrim",
        "Provenance", "SessionPrim", "GateStatusPrim", "MerkleRootPrim",
        "InquiryPrim", "MotorPrim", "SkillPrim", "MultipliersPrim",
        "IntakeHistoryPrim",
    }
    actual = set(POLICY_TABLE)
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        raise RuntimeError(
            f"POLICY_TABLE coverage mismatch: missing={missing}, extra={extra}"
        )
    # Confirm every INHERIT entry has a resolution path
    for tn, p in POLICY_TABLE.items():
        if p == Policy.INHERIT:
            resolved = resolve_policy(tn)
            if resolved == Policy.INHERIT:
                raise RuntimeError(f"INHERIT chain from {tn!r} does not terminate")


_validate_table_completeness()
