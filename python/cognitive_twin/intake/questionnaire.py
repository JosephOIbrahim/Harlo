"""Adaptive neuropsych-informed intake questionnaire.

Dimensions probed:
- Associative vs. Linear thinking → surprise_threshold
- Detail-oriented vs. Big-picture → reconstruction_threshold, detail_orientation
- Attention sustain vs. Burst → hebbian_alpha
- Stress tolerance → allostatic_threshold

Patch 3: Continuous [0.0, 1.0] float scoring with deterministic linear interpolation.
Patch 6: Semantic ceiling detection via user_disengaged flag.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IntakeQuestion:
    """A single intake question."""
    question_id: str
    dimension: str              # associativity, detail, attention, stress
    text: str
    anchors: tuple[str, str]    # (low_anchor, high_anchor) for scoring guidance


# Fixed question bank — deterministic ordering
QUESTION_BANK: list[IntakeQuestion] = [
    IntakeQuestion(
        question_id="q1_assoc",
        dimension="associativity",
        text="When you encounter a new idea, do you tend to connect it to many other concepts, or do you prefer to understand it step by step on its own terms?",
        anchors=("step by step", "connect to many"),
    ),
    IntakeQuestion(
        question_id="q2_detail",
        dimension="detail",
        text="When reviewing your own work, do you focus more on the overall structure and flow, or on specific details and edge cases?",
        anchors=("overall structure", "specific details"),
    ),
    IntakeQuestion(
        question_id="q3_attention",
        dimension="attention",
        text="Do you work best in sustained deep-focus sessions, or in shorter bursts of intense concentration?",
        anchors=("sustained focus", "short bursts"),
    ),
    IntakeQuestion(
        question_id="q4_stress",
        dimension="stress",
        text="When working under time pressure, does your thinking become sharper or more scattered?",
        anchors=("more scattered", "sharper"),
    ),
    IntakeQuestion(
        question_id="q5_assoc2",
        dimension="associativity",
        text="Do you find it easier to explain ideas through analogies and metaphors, or through precise definitions?",
        anchors=("precise definitions", "analogies"),
    ),
    IntakeQuestion(
        question_id="q6_detail2",
        dimension="detail",
        text="When learning something new, do you prefer to see the big picture first, or dive into the specifics?",
        anchors=("big picture first", "specifics first"),
    ),
]

# Disengagement detection patterns
_DISMISSAL_PATTERNS = frozenset({
    "whatever", "skip", "don't care", "dont care", "doesn't matter",
    "doesnt matter", "idk", "i don't know", "next", "pass", "meh",
    "just use defaults", "use defaults", "default", "n/a", "na",
})


@dataclass
class IntakeSession:
    """State for an in-progress intake session."""
    current_index: int = 0
    answers: dict[str, float] = field(default_factory=dict)  # question_id → [0.0, 1.0]
    raw_answers: dict[str, str] = field(default_factory=dict)  # question_id → raw text
    user_disengaged: bool = False
    completed: bool = False

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "current_index": self.current_index,
            "answers": dict(self.answers),
            "raw_answers": dict(self.raw_answers),
            "user_disengaged": self.user_disengaged,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> IntakeSession:
        """Deserialize from dict."""
        return cls(
            current_index=d.get("current_index", 0),
            answers=d.get("answers", {}),
            raw_answers=d.get("raw_answers", {}),
            user_disengaged=d.get("user_disengaged", False),
            completed=d.get("completed", False),
        )


def get_next_question(session: IntakeSession) -> Optional[IntakeQuestion]:
    """Get the next question, or None if intake is complete."""
    if session.completed or session.user_disengaged:
        return None
    if session.current_index >= len(QUESTION_BANK):
        return None
    return QUESTION_BANK[session.current_index]


def score_answer(answer: str, question: IntakeQuestion) -> float:
    """Score an answer on a continuous [0.0, 1.0] scale.

    Patch 3: Deterministic linear interpolation, not bucketed categories.

    Scoring heuristic based on keyword proximity to anchors:
    - Words matching low_anchor → score toward 0.0
    - Words matching high_anchor → score toward 1.0
    - Neutral/mixed → 0.5
    """
    answer_lower = answer.lower().strip()
    low_anchor = question.anchors[0].lower()
    high_anchor = question.anchors[1].lower()

    low_words = set(low_anchor.split())
    high_words = set(high_anchor.split())
    answer_words = set(answer_lower.split())

    low_overlap = len(answer_words & low_words)
    high_overlap = len(answer_words & high_words)

    total = low_overlap + high_overlap
    if total == 0:
        return 0.5  # Neutral

    # Linear interpolation: 0.0 = fully low, 1.0 = fully high
    return high_overlap / total


def detect_disengagement(
    answer: str,
    session: IntakeSession,
) -> bool:
    """Detect semantic disengagement (Patch 6).

    Triggers on:
    - Explicit dismissal language
    - Identical answers to different questions
    - NOT on answer length (TERSE-safe)
    """
    answer_lower = answer.lower().strip()

    # Explicit dismissal
    if answer_lower in _DISMISSAL_PATTERNS:
        return True

    # Identical answers to different questions
    if len(session.raw_answers) >= 2:
        prev_answers = list(session.raw_answers.values())
        if all(a.lower().strip() == answer_lower for a in prev_answers[-2:]):
            return True

    return False


def process_answer(
    session: IntakeSession,
    answer: str,
) -> IntakeSession:
    """Process a user answer and advance the session.

    Returns updated session with score recorded and index advanced.
    """
    # Check disengagement
    if detect_disengagement(answer, session):
        return IntakeSession(
            current_index=session.current_index,
            answers=dict(session.answers),
            raw_answers=dict(session.raw_answers),
            user_disengaged=True,
            completed=False,
        )

    # Score the answer
    question = QUESTION_BANK[session.current_index]
    score = score_answer(answer, question)

    new_answers = dict(session.answers)
    new_answers[question.question_id] = score

    new_raw = dict(session.raw_answers)
    new_raw[question.question_id] = answer

    new_index = session.current_index + 1
    completed = new_index >= len(QUESTION_BANK)

    return IntakeSession(
        current_index=new_index,
        answers=new_answers,
        raw_answers=new_raw,
        user_disengaged=False,
        completed=completed,
    )
