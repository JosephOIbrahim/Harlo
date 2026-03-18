"""Inquiry Engine — Core DMN/Co-Evolution synthesis.

The Twin's voice that asks, not answers.
Orchestrates all inquiry subsystems:
- Apophenia guard (S1)
- Sincerity gate (S8)
- Rupture & repair (S3)
- Crystallization (S7)
- Apoptosis (S5)
- Timing
- Consent
- DMN window (S6)

S2: Inquiry outputs bypass Elenchus truth (tone only). Handled by brainstem.
S4: Utility mode mutes DMN. Behavioral traces invisible.
Rule 1: No blocking waits, no infinite loops.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

from .types import InquiryType, TTL_HOURS
from .apophenia_guard import EvidenceBundle, evaluate as guard_evaluate
from .sincerity_gate import SincerityClass, classify as sincerity_classify
from .rupture_repair import RuptureLedger
from .crystallization import CrystallizationStore
from .threshold_reversion import PenaltyLedger
from .apoptosis import InquiryVitality, sweep_expired
from .timing import TimingState
from .consent import ConsentManager
from .dmn_window import DMNWindow, SynthesisCandidate


@dataclass
class Inquiry:
    """A generated inquiry ready for potential surfacing."""
    inquiry_id: str
    inquiry_type: InquiryType
    hypothesis: str
    alt_hypothesis: str
    question_text: str
    evidence_count: int
    confidence: float
    created_at: float = field(default_factory=time.time)
    surfaced: bool = False
    responded: bool = False
    topic_key: str = ""


@dataclass
class InquiryResponse:
    """User's response to a surfaced inquiry."""
    inquiry_id: str
    response_text: str
    sincerity: SincerityClass = SincerityClass.SINCERE
    accepted: bool = True
    timestamp: float = field(default_factory=time.time)


def _make_id(hypothesis: str, ts: float) -> str:
    """Generate a deterministic inquiry ID."""
    raw = f"{hypothesis}:{ts}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class InquiryEngine:
    """Core inquiry engine. The Twin's voice that asks, not answers.

    Stateful but event-driven. No background threads, no polling.
    All methods are called in response to events.
    """

    def __init__(self) -> None:
        self.rupture_ledger = RuptureLedger()
        self.crystal_store = CrystallizationStore()
        self.penalty_ledger = PenaltyLedger()
        self.timing = TimingState()
        self.consent = ConsentManager()
        self.dmn_window = DMNWindow()

        # Active inquiries (not yet expired)
        self._active: dict[str, Inquiry] = {}
        self._vitalities: list[InquiryVitality] = []

    # ------------------------------------------------------------------
    # Observation intake
    # ------------------------------------------------------------------

    def observe(self, content: str, category: InquiryType, weight: float = 1.0) -> None:
        """Record a behavioral observation during the session.

        S4: If in utility mode, this is a no-op (traces invisible).
        """
        if self.timing.utility_mode:
            return
        self.dmn_window.add_observation(content, category, weight)

    # ------------------------------------------------------------------
    # Synthesis (session exit)
    # ------------------------------------------------------------------

    def synthesize_on_exit(self, abort_check=None) -> list[Inquiry]:
        """S6: Run DMN synthesis at session exit.

        Returns generated inquiries that passed all guards.
        """
        candidates = self.dmn_window.synthesize(abort_check=abort_check)
        inquiries: list[Inquiry] = []

        for candidate in candidates:
            if abort_check and abort_check():
                break
            inquiry = self._process_candidate(candidate)
            if inquiry is not None:
                inquiries.append(inquiry)

        return inquiries

    def _process_candidate(self, candidate: SynthesisCandidate) -> Inquiry | None:
        """Process a synthesis candidate through all guards.

        Returns an Inquiry if it passes, None otherwise.
        """
        topic_key = f"{candidate.inquiry_type.value}:{candidate.hypothesis[:50]}"

        # Consent check
        if not self.consent.is_type_allowed(candidate.inquiry_type):
            return None
        if not self.consent.is_allowed(topic_key):
            return None

        # S3: Rupture check — blocked topics
        if self.rupture_ledger.is_topic_blocked(topic_key):
            return None

        # S1: Apophenia guard
        bundle = EvidenceBundle(
            observations=candidate.supporting_observations,
            hypothesis=candidate.hypothesis,
            alt_hypothesis=candidate.alt_hypothesis,
            depth=self._depth_for_type(candidate.inquiry_type),
        )
        guard_result = guard_evaluate(bundle)
        if not guard_result.passed:
            return None

        # Penalty check (mean-reversion)
        penalty = self.penalty_ledger.effective_penalty(topic_key)
        if penalty > 1.0:
            return None

        # All guards passed — create inquiry
        now = time.time()
        inquiry_id = _make_id(candidate.hypothesis, now)

        inquiry = Inquiry(
            inquiry_id=inquiry_id,
            inquiry_type=candidate.inquiry_type,
            hypothesis=candidate.hypothesis,
            alt_hypothesis=candidate.alt_hypothesis,
            question_text=self._format_question(candidate),
            evidence_count=len(candidate.supporting_observations),
            confidence=candidate.confidence,
            created_at=now,
            topic_key=topic_key,
        )

        # Register vitality for apoptosis
        vitality = InquiryVitality(
            inquiry_id=inquiry_id,
            inquiry_type=candidate.inquiry_type,
            created_at=now,
        )
        self._vitalities.append(vitality)
        self._active[inquiry_id] = inquiry

        return inquiry

    # ------------------------------------------------------------------
    # Surfacing
    # ------------------------------------------------------------------

    def get_surfaceable(self, allostatic_load: float = 0.0) -> Inquiry | None:
        """Get the next inquiry to surface, if timing allows.

        Returns None if no inquiry should be surfaced right now.
        """
        if not self.timing.can_surface(allostatic_load=allostatic_load):
            return None

        # Sweep expired first
        self._sweep()

        # Find best unsurfaced inquiry
        best: Inquiry | None = None
        best_score = -1.0

        for inquiry in self._active.values():
            if inquiry.surfaced:
                continue
            score = inquiry.confidence - self.penalty_ledger.effective_penalty(inquiry.topic_key)
            if score > best_score:
                best_score = score
                best = inquiry

        if best is not None:
            best.surfaced = True
            self.timing.record_surfaced()

        return best

    # ------------------------------------------------------------------
    # Response handling
    # ------------------------------------------------------------------

    def handle_response(self, inquiry_id: str, response_text: str) -> InquiryResponse:
        """Handle a user's response to a surfaced inquiry.

        Applies S8 sincerity gate and S3 rupture/repair logic.
        """
        sincerity_result = sincerity_classify(response_text)
        inquiry = self._active.get(inquiry_id)

        # Determine if this is a rejection
        is_rejection = sincerity_result.classification in (
            SincerityClass.EXASPERATED,
            SincerityClass.SARCASTIC,
        )

        response = InquiryResponse(
            inquiry_id=inquiry_id,
            response_text=response_text,
            sincerity=sincerity_result.classification,
            accepted=not is_rejection,
        )

        if inquiry is not None:
            inquiry.responded = True

            if is_rejection:
                # S3: Record rejection with weight 2.0
                self.rupture_ledger.record_rejection(
                    inquiry_id=inquiry_id,
                    topic_key=inquiry.topic_key,
                    response_text=response_text,
                )
                # Add penalty
                self.penalty_ledger.add_penalty(inquiry.topic_key, 0.5)

        return response

    def should_offer_stop(self, inquiry_id: str) -> bool:
        """S3: Check if we should offer to stop asking about this topic."""
        inquiry = self._active.get(inquiry_id)
        if inquiry is None:
            return False
        return self.rupture_ledger.should_offer_stop(inquiry.topic_key)

    # ------------------------------------------------------------------
    # Crystallization
    # ------------------------------------------------------------------

    def attempt_crystallize(
        self,
        trace_id: str,
        topic_key: str,
        observations: list[str],
        decay_rate: float,
        preservation_score: float,
    ) -> bool:
        """S7: Attempt to crystallize a trace. Returns True if crystallized."""
        result = self.crystal_store.attempt_crystallize(
            trace_id=trace_id,
            topic_key=topic_key,
            observations=observations,
            decay_rate=decay_rate,
            preservation_score=preservation_score,
        )
        return result is not None

    # ------------------------------------------------------------------
    # Legacy compatibility
    # ------------------------------------------------------------------

    @staticmethod
    def synthesize(
        patterns: list,
        elenchus_state: dict | None = None,
        max_candidates: int = 2,
    ) -> list:
        """Legacy synthesis interface for backward compatibility.

        Filters through apophenia guard before returning.
        """
        candidates = []
        for pattern in patterns:
            inquiry = {
                "type": pattern.get("type", InquiryType.PATTERN.value),
                "observations": pattern.get("observations", 0),
                "depth": pattern.get("depth", "standard"),
                "content": pattern.get("content", ""),
                "alternative_hypothesis": pattern.get("alternative", "Random coincidence"),
                "confidence": pattern.get("confidence", 0.0),
            }
            obs_count = inquiry["observations"]
            if isinstance(obs_count, int) and obs_count >= 5:
                candidates.append(inquiry)

        candidates.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return candidates[:max_candidates]

    @staticmethod
    def prepare_traces_for_dmn(traces: list, utility_mode: bool = False) -> list:
        """Prepare traces for DMN synthesis.

        Excludes utility behavioral traces (S4).
        """
        if utility_mode:
            return [t for t in traces if t.get("trace_type") == "semantic"]
        return traces

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def enter_utility_mode(self) -> None:
        """S4: Mute DMN. Behavioral traces invisible."""
        self.timing.enter_utility_mode()

    def exit_utility_mode(self) -> None:
        """Exit utility mode."""
        self.timing.exit_utility_mode()

    def new_session(self) -> None:
        """Reset for a new session."""
        self.dmn_window.clear()
        self.timing = TimingState()
        self._sweep()
        self.penalty_ledger.prune_negligible()

    def _sweep(self) -> None:
        """S5: Remove expired inquiries."""
        expired_ids, self._vitalities = sweep_expired(self._vitalities)
        for eid in expired_ids:
            self._active.pop(eid, None)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _depth_for_type(inquiry_type: InquiryType) -> int:
        """Map inquiry type to evidence depth level."""
        return {
            InquiryType.PATTERN: 1,
            InquiryType.CONTRADICTION: 2,
            InquiryType.DRIFT: 2,
            InquiryType.GROWTH: 1,
            InquiryType.EXISTENTIAL: 3,
        }.get(inquiry_type, 1)

    @staticmethod
    def _format_question(candidate: SynthesisCandidate) -> str:
        """Format a synthesis candidate into a question string.

        Placeholder — in production this calls the LLM for
        natural phrasing. The structure is ready for that.
        """
        return (
            f"I've noticed something about your {candidate.inquiry_type.value} "
            f"— {candidate.hypothesis}. What are your thoughts?"
        )

    def get_stats(self) -> dict[str, Any]:
        """Return engine statistics for diagnostics."""
        return {
            "active_inquiries": len(self._active),
            "crystallized_traces": self.crystal_store.count(),
            "pending_observations": len(self.dmn_window.observations),
            "rejected_topics": self.rupture_ledger.get_all_rejected_topics(),
            "blocked_keys": self.consent.get_blocked_keys(),
            "utility_mode": self.timing.utility_mode,
        }
