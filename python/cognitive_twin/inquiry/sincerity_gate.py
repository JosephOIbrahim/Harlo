"""Sincerity Gate — S8: Response classification.

Classifies user responses to inquiries as:
sincere / sarcastic / exasperated / performative / uncertain.

This determines how the Twin updates its model after an inquiry.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SincerityClass(Enum):
    SINCERE = "sincere"
    SARCASTIC = "sarcastic"
    EXASPERATED = "exasperated"
    PERFORMATIVE = "performative"
    UNCERTAIN = "uncertain"


# Signal words/phrases for heuristic classification
_SARCASM_SIGNALS = frozenset({
    "sure", "right", "yeah right", "whatever", "obviously",
    "totally", "wow", "genius", "brilliant", "no kidding",
})

_EXASPERATION_SIGNALS = frozenset({
    "stop", "enough", "again", "leave me alone", "not this again",
    "drop it", "seriously", "i said", "already told you",
})

_PERFORMATIVE_SIGNALS = frozenset({
    "i guess", "if you say so", "fine", "sure whatever",
    "i suppose", "okay fine", "alright alright",
})

_UNCERTAIN_SIGNALS = frozenset({
    "i don't know", "maybe", "not sure", "hard to say",
    "i think", "possibly", "kind of", "sort of",
})


@dataclass
class SincerityResult:
    """Result of sincerity classification."""
    classification: SincerityClass
    confidence: float  # 0.0 to 1.0
    signals_matched: list[str]


def classify(response_text: str) -> SincerityResult:
    """Classify a response's sincerity.

    Heuristic classifier. In production this would be backed by
    an LLM judge; the structure is ready for that upgrade.
    """
    text = response_text.lower().strip()

    matches: dict[SincerityClass, list[str]] = {
        SincerityClass.SARCASTIC: [],
        SincerityClass.EXASPERATED: [],
        SincerityClass.PERFORMATIVE: [],
        SincerityClass.UNCERTAIN: [],
    }

    for signal in _SARCASM_SIGNALS:
        if signal in text:
            matches[SincerityClass.SARCASTIC].append(signal)

    for signal in _EXASPERATION_SIGNALS:
        if signal in text:
            matches[SincerityClass.EXASPERATED].append(signal)

    for signal in _PERFORMATIVE_SIGNALS:
        if signal in text:
            matches[SincerityClass.PERFORMATIVE].append(signal)

    for signal in _UNCERTAIN_SIGNALS:
        if signal in text:
            matches[SincerityClass.UNCERTAIN].append(signal)

    # Pick the class with most signal matches
    best_class = SincerityClass.SINCERE
    best_count = 0
    best_signals: list[str] = []

    for cls, signals in matches.items():
        if len(signals) > best_count:
            best_class = cls
            best_count = len(signals)
            best_signals = signals

    # Confidence: more signals = higher confidence in non-sincere
    if best_count == 0:
        confidence = 0.6  # Default moderate confidence for sincere
    else:
        confidence = min(0.5 + 0.15 * best_count, 0.95)

    return SincerityResult(
        classification=best_class,
        confidence=confidence,
        signals_matched=best_signals,
    )
