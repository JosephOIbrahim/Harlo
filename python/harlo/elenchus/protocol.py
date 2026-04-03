"""Core Generate-Verify-Revise (GVR) protocol — the Elenchus loop.

Rule 13: Max 3 GVR cycles (ADHD guard).  After cycle 3, FIXABLE is promoted
         to UNPROVABLE.
Rule 16: UNPROVABLE is dignified — carries metadata (reason, what_would_help,
         partial_progress).
Rule 12: Only VERIFIED resolutions become reflexes.
Rule 15: SPEC_GAMED results are never consolidated.

The loop:
    1. verify(intent, output) — trace excluded (Rule 11)
    2. If VERIFIED -> return
    3. If SPEC_GAMED -> return (never consolidate)
    4. If FIXABLE and cycle < max_cycles -> revise and loop
    5. If FIXABLE and cycle >= max_cycles -> promote to UNPROVABLE
"""

from __future__ import annotations

from typing import Callable, Optional

from .states import VerificationState, VerificationResult
from .verifier import verify
from .spec_gaming import detect_spec_gaming
from .intent import check_intent_alignment
from .reviser import revise
from .depth import get_depth


def _describe_flaw(intent: str, output) -> str:
    """Build a human-readable flaw description from heuristic checks."""
    text = str(output).strip() if output else ""

    if not text:
        return "Output is empty or None"

    # Check spec-gaming first
    gaming = detect_spec_gaming(intent, output)
    if gaming:
        return gaming

    # Check alignment
    if not check_intent_alignment(intent, output):
        return "Output does not adequately address the original intent"

    # Coherence — repetition
    words = text.split()
    if len(words) >= 6:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.15:
            return "Output is excessively repetitive"

    # Completeness — truncation
    lower = text.lower()
    for sig in ("...", "to be continued", "[truncated]", "[cut off]"):
        if lower.endswith(sig):
            return f"Output appears truncated (ends with '{sig}')"

    return "Output has structural or completeness issues"


def run_gvr(
    intent: str,
    output,
    generator_fn: Optional[Callable] = None,
    domain: str = "general",
    max_cycles: int = 3,
    context: Optional[dict] = None,
) -> VerificationResult:
    """Run the Generate-Verify-Revise loop.

    Args:
        intent: The original user intent.
        output: The initial output to verify.
        generator_fn: Optional callable(intent, output, flaw, context) -> revised.
                      Used by the reviser to produce patched outputs.
        domain: Domain key for depth-tuned verification (e.g. "medical").
        max_cycles: Maximum GVR iterations (Rule 13, hard cap at 3).
        context: Extra context dict passed through to the reviser.

    Returns:
        VerificationResult with terminal state and metadata.
    """
    # Rule 13: hard cap at 3 cycles
    max_cycles = min(max_cycles, 3)

    # Domain depth can further reduce effective cycles
    domain_depth = get_depth(domain)
    effective_max = min(max_cycles, domain_depth)

    ctx = context or {}
    current_output = output
    flaw_history: list[str] = []

    for cycle in range(1, effective_max + 1):
        # ---- Step 1: Verify (trace-excluded, Rule 11) ----
        state = verify(intent, current_output, reasoning_trace=None)

        # ---- Step 2: VERIFIED -> return immediately ----
        if state is VerificationState.VERIFIED:
            return VerificationResult(
                state=VerificationState.VERIFIED,
                cycle_count=cycle,
                original_intent=intent,
            )

        # ---- Step 3: SPEC_GAMED -> return, never consolidate (Rule 15) ----
        if state is VerificationState.SPEC_GAMED:
            gaming_flaw = detect_spec_gaming(intent, current_output)
            return VerificationResult(
                state=VerificationState.SPEC_GAMED,
                cycle_count=cycle,
                flaw=gaming_flaw or "Spec-gaming detected",
                original_intent=intent,
            )

        # ---- Step 4: FIXABLE -> describe flaw and attempt revision ----
        flaw = _describe_flaw(intent, current_output)
        flaw_history.append(flaw)

        if cycle < effective_max and generator_fn is not None:
            current_output = revise(
                intent=intent,
                output=current_output,
                flaw=flaw,
                generator_fn=generator_fn,
                context={**ctx, "cycle": cycle, "domain": domain},
            )
            # Loop back to verify the revised output
            continue

        # ---- Step 5: Exhausted cycles -> promote FIXABLE to UNPROVABLE ----
        # Rule 13 + Rule 16
        return VerificationResult(
            state=VerificationState.UNPROVABLE,
            cycle_count=cycle,
            flaw=flaw,
            original_intent=intent,
            unprovable_reason=(
                f"Exhausted {cycle} GVR cycle(s) without resolution. "
                f"Last flaw: {flaw}"
            ),
            what_would_help=(
                "A more capable generator_fn, additional context, "
                "or manual intervention may resolve the flaw."
            ),
            partial_progress={
                "last_output": str(current_output)[:500],
                "flaw_history": flaw_history,
                "cycles_used": cycle,
            },
        )

    # Edge case: effective_max <= 0 (domain depth is 0 somehow)
    return VerificationResult(
        state=VerificationState.DEFERRED,
        cycle_count=0,
        original_intent=intent,
        unprovable_reason="No verification cycles were executed (effective depth=0).",
        what_would_help="Increase domain verification depth or max_cycles.",
    )
