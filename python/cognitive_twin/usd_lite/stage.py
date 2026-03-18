"""BrainStage -- top-level USD container for the entire brain state.

Every subsystem writes to its own subtree.  LIVRPS composition determines
what wins when subsystems disagree.

Patch 11+: ``BrainStage.__eq__`` uses ``math.isclose(rel_tol=1e-9)`` for
float fields and exact equality for everything else, so that
``parse(serialize(stage)) == stage`` survives float round-trip rounding.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, fields
from enum import Enum
from typing import Optional

from .prims import (
    ElenchusPrim,
    AssociationPrim,
    CognitiveProfilePrim,
    CompositionPrim,
    InquiryContainerPrim,
    MotorContainerPrim,
    SessionPrim,
    SkillsContainerPrim,
)

_FLOAT_REL_TOL = 1e-9


def _deep_eq(a: object, b: object) -> bool:
    """Recursively compare two objects with float tolerance.

    - float: ``math.isclose(rel_tol=1e-9)``
    - list: element-wise
    - dict: key equality + value-wise
    - dataclass: field-wise
    - Enum: exact value equality
    - everything else: ``==``
    """
    if type(a) is not type(b):
        return False

    if isinstance(a, float):
        # Handle NaN, inf, and normal floats
        if math.isnan(a) and math.isnan(b):
            return True
        return math.isclose(a, b, rel_tol=_FLOAT_REL_TOL)

    if isinstance(a, list):
        if len(a) != len(b):  # type: ignore[arg-type]
            return False
        return all(_deep_eq(x, y) for x, y in zip(a, b))  # type: ignore[arg-type]

    if isinstance(a, dict):
        if a.keys() != b.keys():  # type: ignore[union-attr]
            return False
        return all(_deep_eq(a[k], b[k]) for k in a)  # type: ignore[index]

    if isinstance(a, Enum):
        return a.value == b.value  # type: ignore[union-attr]

    # Dataclass check (has __dataclass_fields__)
    if hasattr(a, "__dataclass_fields__"):
        for f in fields(a):  # type: ignore[arg-type]
            if not _deep_eq(getattr(a, f.name), getattr(b, f.name)):
                return False
        return True

    # Fallback: exact equality
    return a == b


@dataclass
class BrainStage:
    """Root container for the entire brain state as a USD stage.

    Every subsystem writes to its own subtree.  LIVRPS composition
    determines what wins when subsystems disagree.
    """
    association: AssociationPrim = field(default_factory=AssociationPrim)
    composition: CompositionPrim = field(default_factory=CompositionPrim)
    elenchus: ElenchusPrim = field(default_factory=ElenchusPrim)
    session: Optional[SessionPrim] = None
    inquiry: InquiryContainerPrim = field(default_factory=InquiryContainerPrim)
    motor: MotorContainerPrim = field(default_factory=MotorContainerPrim)
    skills: SkillsContainerPrim = field(default_factory=SkillsContainerPrim)
    cognitive_profile: CognitiveProfilePrim = field(default_factory=CognitiveProfilePrim)

    def __eq__(self, other: object) -> bool:
        """Compare with float tolerance for round-trip fidelity."""
        if not isinstance(other, BrainStage):
            return NotImplemented
        return _deep_eq(self, other)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "association": self.association.to_dict(),
            "composition": self.composition.to_dict(),
            "elenchus": self.elenchus.to_dict(),
            "session": self.session.to_dict() if self.session else None,
            "inquiry": self.inquiry.to_dict(),
            "motor": self.motor.to_dict(),
            "skills": self.skills.to_dict(),
            "cognitive_profile": self.cognitive_profile.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> BrainStage:
        """Deserialize from dict."""
        sess = d.get("session")
        return cls(
            association=AssociationPrim.from_dict(d.get("association", {})),
            composition=CompositionPrim.from_dict(d.get("composition", {})),
            elenchus=ElenchusPrim.from_dict(d.get("elenchus", {})),
            session=SessionPrim.from_dict(sess) if sess else None,
            inquiry=InquiryContainerPrim.from_dict(d.get("inquiry", {})),
            motor=MotorContainerPrim.from_dict(d.get("motor", {})),
            skills=SkillsContainerPrim.from_dict(d.get("skills", {})),
            cognitive_profile=CognitiveProfilePrim.from_dict(
                d.get("cognitive_profile", {})
            ),
        )
