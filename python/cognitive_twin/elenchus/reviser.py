"""Targeted flaw patching for the GVR loop.

The reviser generates a corrected output by patching a specific flaw.
NOT a restart — targeted patch. Full trace is available for revision
(unlike verify which is trace-excluded per Rule 11).
"""

from __future__ import annotations

from typing import Callable, Optional


def revise(
    intent: str,
    output,
    flaw: str,
    generator_fn: Optional[Callable] = None,
    context: Optional[dict] = None,
):
    """Generate a revised output that patches the specific flaw.

    Args:
        intent: The original intent.
        output: The current (flawed) output.
        flaw: Description of the flaw to fix.
        generator_fn: Callable(intent, output, flaw, context) -> revised_output.
                       If None, returns the original output unchanged.
        context: Additional context for the generator.

    Returns:
        The revised output (type matches generator output, or original).
    """
    if generator_fn is None:
        return output

    ctx = context or {}
    return generator_fn(intent, output, flaw, ctx)
