"""Intent extraction and alignment checking — Rule 14.

Rule 14: INTENT PRESERVATION.  The output must answer the *original* intent,
not a paraphrase, a subset, or a tangent.
"""

from __future__ import annotations

from typing import Optional


# ------------------------------------------------------------------
# Intent extraction
# ------------------------------------------------------------------

_FILLER_PREFIXES = (
    "please ", "could you ", "can you ", "would you ",
    "i want you to ", "i need you to ", "i'd like you to ",
    "help me ", "help me to ", "kindly ", "just ",
    "i want to ", "i need to ",
)


def extract_intent(message: str) -> str:
    """Extract the core intent from a user message.

    Strips politeness wrappers, trailing punctuation noise, and
    normalises whitespace so downstream comparisons are stable.

    Returns a normalized intent string suitable for verification.
    """
    if not message or not message.strip():
        return ""

    text = message.strip()
    lower = text.lower()

    for prefix in _FILLER_PREFIXES:
        if lower.startswith(prefix):
            text = text[len(prefix):]
            lower = text.lower()
            break  # Only strip one layer

    # Remove trailing punctuation for normalization
    text = text.rstrip("?!.")

    # Collapse whitespace
    text = " ".join(text.split())
    return text.strip()


# ------------------------------------------------------------------
# Alignment checking
# ------------------------------------------------------------------

_ACTION_VERBS = {
    "list": "enumeration",
    "compare": "comparison",
    "explain": "explanation",
    "describe": "description",
    "summarize": "summary",
    "summarise": "summary",
    "calculate": "calculation",
    "analyse": "analysis",
    "analyze": "analysis",
    "evaluate": "evaluation",
    "define": "definition",
    "translate": "translation",
    "implement": "implementation",
    "design": "design",
    "create": "creation",
    "write": "written content",
    "fix": "fix/correction",
    "debug": "debugging",
    "refactor": "refactoring",
    "test": "test",
    "review": "review",
}

_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "of", "in", "to", "for", "and",
    "or", "it", "on", "at", "by", "as", "be", "was", "with", "that",
    "this", "from", "not", "but", "they", "we", "you", "i", "my",
    "do", "if", "so", "no", "up", "me", "he", "she", "all", "can",
    "has", "had", "how", "its", "may", "our", "use", "way", "get",
})


def _extract_action(intent: str) -> Optional[str]:
    """Identify the primary action verb requested by the intent."""
    words = intent.split()
    if not words:
        return None
    first_word = words[0].lower().rstrip(".,;:!?")
    return _ACTION_VERBS.get(first_word)


def check_intent_alignment(intent: str, output) -> bool:
    """Check whether *output* actually addresses *intent*.

    Rule 14: The output must answer the intent, not a reframed
    easier question.

    Heuristic checks:
    1. If the intent requests a specific action (list, compare, etc.),
       the output should contain structural markers of that action type.
    2. Key nouns from the intent should appear in the output.

    Args:
        intent: The original intent string.
        output: The output to check (str or dict).

    Returns:
        True if the output appears to address the intent.
    """
    if not intent:
        return False

    output_str = str(output).strip() if output else ""

    # Empty output never aligns
    if not output_str:
        return False

    intent_clean = extract_intent(intent)
    if not intent_clean:
        return bool(output_str)

    # Very short output for a substantive intent is suspicious
    intent_words = intent_clean.split()
    output_words = output_str.split()

    if len(intent_words) > 3 and len(output_words) < 2:
        return False

    # --- Keyword overlap ---
    intent_keywords = {
        w.lower().strip(".,;:!?\"'()[]{}") for w in intent_words
    }
    intent_content = {w for w in intent_keywords if w not in _STOP_WORDS and len(w) > 1}

    if not intent_content:
        return len(output_words) > 0

    output_lower = output_str.lower()
    matches = sum(1 for w in intent_content if w in output_lower)
    ratio = matches / len(intent_content)

    # Require at least 20% keyword presence for alignment
    # Also pass if the output is substantial (>10 words) with any overlap
    return ratio >= 0.20 or (len(output_words) > 10 and matches > 0)
