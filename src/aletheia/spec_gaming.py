"""Spec-gaming detection — Rule 15.

The dominant failure mode of cognitive systems is answering the *wrong*
question correctly.  This module contains heuristic detectors for that
pattern.
"""

from typing import Optional


# ------------------------------------------------------------------
# Keyword-overlap heuristic
# ------------------------------------------------------------------

_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "must", "can", "could", "i", "me", "my",
    "we", "our", "you", "your", "he", "she", "it", "they", "them",
    "this", "that", "these", "those", "of", "in", "to", "for", "with",
    "on", "at", "by", "from", "as", "into", "about", "but", "or", "and",
    "not", "no", "so", "if", "then", "than", "too", "very", "just",
    "also", "more", "some", "any", "all", "each", "both", "such",
    "when", "what", "which", "how", "where", "why", "who", "whom",
})


def _content_words(text: str) -> set:
    """Extract meaningful content words from text."""
    tokens = text.lower().split()
    # Strip basic punctuation from edges
    cleaned = {t.strip(".,;:!?\"'()[]{}") for t in tokens}
    return {w for w in cleaned if w and w not in _STOP_WORDS and len(w) > 1}


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def detect_spec_gaming(intent: str, output) -> Optional[str]:
    """Detect if *output* answers a different question than *intent*.

    Heuristic signals:
    1. **Topic drift** — the output's content words share very little
       overlap with the intent's content words while being substantial
       in length (i.e., it is not merely short/empty but actively
       discusses something else).
    2. **Deflection patterns** — the output explicitly redirects to a
       different topic or restates the question as a different one.

    Returns
    -------
    str or None
        A flaw description if spec-gaming is detected, ``None`` otherwise.
    """
    text = str(output).strip()
    if not text:
        return None  # Empty is handled by the verifier, not here

    intent_words = _content_words(intent)
    output_words = _content_words(text)

    # --- Signal 1: topic drift ---
    if intent_words and output_words:
        overlap = intent_words & output_words
        # If the output is substantial but shares almost no keywords with
        # the intent, it is likely answering a different question.
        if len(output_words) >= 8 and len(overlap) == 0:
            return (
                "Topic drift: output contains no content words from the "
                "original intent — likely answers a different question"
            )
        # Very low overlap ratio on longer outputs
        if len(output_words) >= 15:
            ratio = len(overlap) / len(intent_words) if intent_words else 1.0
            if ratio < 0.05:
                return (
                    "Topic drift: output shares <5% of intent keywords — "
                    "probable spec-gaming"
                )

    # --- Signal 2: deflection patterns ---
    lower_text = text.lower()
    deflection_phrases = [
        "instead, let me",
        "a better question would be",
        "what you really mean is",
        "let me answer a different",
        "i'll address something else",
        "rather than answering that",
        "that's the wrong question",
    ]
    for phrase in deflection_phrases:
        if phrase in lower_text:
            return f"Deflection detected: output contains '{phrase}'"

    return None
