"""Trace-excluded verifier — the core of Elenchus's cognitive immune system.

Rule 11: verify() NEVER receives a reasoning trace.  If the reasoning_trace
parameter is anything other than None the call MUST raise ValueError
immediately.  This is non-negotiable; the build fails otherwise.

The verifier uses heuristic checks (keyword matching, structure validation,
length) so it can run without an LLM call.
"""

from typing import Optional

from .states import VerificationState
from .spec_gaming import detect_spec_gaming
from .intent import check_intent_alignment


# ------------------------------------------------------------------
# Internal heuristic helpers
# ------------------------------------------------------------------

def _is_empty_or_trivial(output) -> bool:
    """Check if the output is empty or trivially short."""
    if output is None:
        return True
    text = str(output).strip()
    return len(text) == 0


def _check_coherence(output) -> Optional[str]:
    """Basic coherence: output should not be self-contradictory noise.

    Returns a flaw description or None.
    """
    text = str(output).strip()

    # Extremely short outputs are suspicious but not incoherent per se
    if len(text) < 2:
        return "Output is effectively empty"

    # Repetition detector — same token repeated many times
    words = text.split()
    if len(words) >= 6:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.15:
            return "Output is excessively repetitive"

    return None


def _check_completeness(intent: str, output) -> Optional[str]:
    """Heuristic completeness: does the output look finished?

    Returns a flaw description or None.
    """
    text = str(output).strip()

    # If the intent asks a question, the output should have some substance
    question_markers = ("?", "what", "how", "why", "when", "where", "which",
                        "explain", "describe", "list", "compare")
    intent_lower = intent.lower()
    is_question = any(m in intent_lower for m in question_markers)

    if is_question and len(text) < 10:
        return "Output too brief for the complexity of the intent"

    # Detect truncation signals
    truncation_signals = ("...", "to be continued", "[truncated]", "[cut off]")
    for sig in truncation_signals:
        if text.lower().endswith(sig):
            return f"Output appears truncated (ends with '{sig}')"

    return None


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def verify(intent: str, output, reasoning_trace=None) -> VerificationState:
    """Verify *output* against *intent* using heuristic checks.

    CRITICAL — Rule 11: reasoning_trace MUST be None.
    If it is not None a ``ValueError`` is raised immediately.

    Checks (in order):
    1. Trace exclusion guard.
    2. Empty / trivial output.
    3. Spec-gaming detection (Rule 15).
    4. Intent alignment (Rule 14).
    5. Coherence.
    6. Completeness.

    Returns
    -------
    VerificationState
        VERIFIED  — all checks pass.
        FIXABLE   — a correctable flaw was found.
        SPEC_GAMED — output answers a different question.
    """
    # ---- Rule 11: trace exclusion ----
    if reasoning_trace is not None:
        raise ValueError(
            "RULE 11 VIOLATION: reasoning_trace must be None. "
            "Trace exclusion is mandatory."
        )

    # ---- Trivial output ----
    if _is_empty_or_trivial(output):
        return VerificationState.FIXABLE

    # ---- Spec-gaming (Rule 15) ----
    gaming_flaw = detect_spec_gaming(intent, output)
    if gaming_flaw is not None:
        return VerificationState.SPEC_GAMED

    # ---- Intent alignment (Rule 14) ----
    if not check_intent_alignment(intent, output):
        return VerificationState.FIXABLE

    # ---- Coherence ----
    coherence_flaw = _check_coherence(output)
    if coherence_flaw is not None:
        return VerificationState.FIXABLE

    # ---- Completeness ----
    completeness_flaw = _check_completeness(intent, output)
    if completeness_flaw is not None:
        return VerificationState.FIXABLE

    return VerificationState.VERIFIED
