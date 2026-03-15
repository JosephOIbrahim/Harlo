"""Full Twin generation loop — the bridge between human query and LLM response.

Pipeline:
    user query → semantic recall (context) → inject context into prompt
    → provider.generate() → aletheia verify → GVR if needed → return

This module wires together:
    - src/encoder (semantic recall for context)
    - src/provider (LLM generation)
    - src/aletheia (verification + GVR)
    - src/modulation/barrier (optional structured output validation)
"""

from __future__ import annotations

from typing import Optional

from ..aletheia.protocol import run_gvr
from ..aletheia.states import VerificationResult, VerificationState


def generate(
    query: str,
    provider,
    db_path: str,
    domain: str = "general",
    encoder_type: str = "semantic",
    recall_depth: str = "normal",
    system_prompt: str | None = None,
    validate_barrier: bool = False,
) -> dict:
    """Run the full Twin generation loop.

    Steps:
        1. Semantic recall — retrieve relevant context traces
        2. Build augmented prompt with recalled context
        3. Generate initial response via LLM provider
        4. Run Aletheia GVR verification (with provider as revision generator)
        5. Optionally validate through Blood-Brain Barrier

    Args:
        query: The user's question or prompt.
        provider: An LLM provider implementing the Provider protocol.
        db_path: Path to the SQLite trace database.
        domain: Domain key for verification depth tuning.
        encoder_type: "semantic" or "lexical" for recall encoding.
        recall_depth: "normal" (k=5) or "deep" (k=15) for recall.
        system_prompt: Optional system prompt override.
        validate_barrier: If True, validate output against barrier schema.

    Returns:
        dict with keys:
            response (str): The final generated text.
            verification (dict): Aletheia verification result.
            context_traces (list): Traces used for context.
            confidence (float): Recall confidence score.
            model (str): Provider model name.
    """
    # ---- Step 1: Semantic recall for context ----
    recall_result = _recall_context(db_path, query, encoder_type, recall_depth)
    context_traces = recall_result.get("traces", [])
    confidence = recall_result.get("confidence", 0.0)
    recalled_context = recall_result.get("context", "")

    # ---- Step 2: Build augmented prompt ----
    augmented_prompt = _build_augmented_prompt(query, recalled_context, system_prompt)

    # ---- Step 3: Generate initial response ----
    response = provider.generate(augmented_prompt)

    # ---- Step 4: Aletheia GVR verification ----
    def _generator_fn(intent: str, output, flaw: str, context: dict) -> str:
        """Revision generator: asks the provider to fix the flaw."""
        revision_prompt = (
            f"The following response to the query '{intent}' has a flaw:\n\n"
            f"Response: {str(output)[:1000]}\n\n"
            f"Flaw: {flaw}\n\n"
            f"Please provide a corrected response that addresses this flaw."
        )
        return provider.generate(revision_prompt)

    gvr_result: VerificationResult = run_gvr(
        intent=query,
        output=response,
        generator_fn=_generator_fn,
        domain=domain,
    )

    # If GVR produced a revised output, use it
    final_response = response
    if gvr_result.partial_progress and "last_output" in gvr_result.partial_progress:
        if gvr_result.state is not VerificationState.SPEC_GAMED:
            final_response = gvr_result.partial_progress["last_output"]

    # ---- Step 5: Optional barrier validation ----
    barrier_result = None
    if validate_barrier:
        barrier_result = _validate_barrier(final_response)

    return {
        "response": final_response,
        "verification": gvr_result.to_dict(),
        "context_traces": context_traces,
        "confidence": confidence,
        "model": provider.model_name,
        "barrier": barrier_result,
    }


def _recall_context(
    db_path: str, query: str, encoder_type: str, depth: str
) -> dict:
    """Recall relevant traces for context injection.

    Tries the requested encoder first. If lexical is requested but the
    hippocampus Rust module is not available, falls back to semantic
    recall so that stored traces are still found.
    """
    if encoder_type == "semantic":
        from ..encoder import semantic_recall
        return semantic_recall(db_path, query, depth=depth)

    # Lexical path via Rust — fall back to semantic if unavailable
    try:
        from cognitive_twin import hippocampus
        return hippocampus.py_recall(query, depth=depth, db_path=db_path)
    except ImportError:
        from ..encoder import semantic_recall
        return semantic_recall(db_path, query, depth=depth)


def _build_augmented_prompt(
    query: str, recalled_context: str, system_prompt: str | None
) -> str:
    """Build the final prompt with recalled context injected."""
    parts = []

    if system_prompt:
        parts.append(system_prompt)

    if recalled_context:
        parts.append(
            "The following context from memory may be relevant:\n"
            f"{recalled_context}\n"
        )

    parts.append(query)
    return "\n\n".join(parts)


def _validate_barrier(response: str) -> dict | None:
    """Optionally validate response through the Blood-Brain Barrier.

    Returns validation result or None if response is not valid JSON.
    """
    try:
        from ..modulation.barrier import validate_llm_output, strip_epigenetic_wash
        validated = validate_llm_output(response)
        core = strip_epigenetic_wash(validated)
        return {"valid": True, "core_memory": core.get("core_memory", {})}
    except Exception as e:
        return {"valid": False, "error": str(e)}
