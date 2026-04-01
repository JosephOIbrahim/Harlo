"""Elenchus verification states and result container.

Defines the possible outcomes of the Generate-Verify-Revise protocol.
Rule 12: Only VERIFIED resolutions become reflexes.
Rule 16: UNPROVABLE carries metadata (reason, what_would_help, partial_progress).
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional


class VerificationState(Enum):
    VERIFIED = "verified"
    FIXABLE = "fixable"
    SPEC_GAMED = "spec_gamed"
    UNPROVABLE = "unprovable"
    DEFERRED = "deferred"


@dataclass
class VerificationResult:
    """Result of a verification cycle or full GVR run.

    Attributes:
        state: Terminal verification state.
        cycle_count: Number of GVR cycles executed.
        flaw: Description of detected flaw (for FIXABLE / SPEC_GAMED).
        original_intent: The intent string that was being verified.
        unprovable_reason: Why verification could not conclude (Rule 16).
        what_would_help: Guidance for future resolution (Rule 16).
        partial_progress: Any salvageable intermediate data (Rule 16).
    """

    state: VerificationState
    cycle_count: int
    flaw: Optional[str] = None
    original_intent: Optional[str] = None
    unprovable_reason: Optional[str] = None
    what_would_help: Optional[str] = None
    partial_progress: Optional[dict] = field(default=None)

    # ------------------------------------------------------------------
    # Convenience predicates
    # ------------------------------------------------------------------

    @property
    def is_verified(self) -> bool:
        """Rule 12: only VERIFIED results may be consolidated into reflexes."""
        return self.state is VerificationState.VERIFIED

    @property
    def is_spec_gamed(self) -> bool:
        return self.state is VerificationState.SPEC_GAMED

    @property
    def is_unprovable(self) -> bool:
        return self.state is VerificationState.UNPROVABLE

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a plain dict (JSON-safe)."""
        d: dict = {
            "state": self.state.value,
            "cycle_count": self.cycle_count,
        }
        if self.flaw is not None:
            d["flaw"] = self.flaw
        if self.original_intent is not None:
            d["original_intent"] = self.original_intent
        if self.unprovable_reason is not None:
            d["unprovable_reason"] = self.unprovable_reason
        if self.what_would_help is not None:
            d["what_would_help"] = self.what_would_help
        if self.partial_progress is not None:
            d["partial_progress"] = self.partial_progress
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "VerificationResult":
        """Deserialise from a plain dict."""
        return cls(
            state=VerificationState(data["state"]),
            cycle_count=data["cycle_count"],
            flaw=data.get("flaw"),
            original_intent=data.get("original_intent"),
            unprovable_reason=data.get("unprovable_reason"),
            what_would_help=data.get("what_would_help"),
            partial_progress=data.get("partial_progress"),
        )
