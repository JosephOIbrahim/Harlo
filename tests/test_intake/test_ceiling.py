"""Gate 4e: Semantic ceiling detection — Patch 6.

Disengagement via user_disengaged flag, NOT answer length.
TERSE-safe: short answers do NOT trigger ceiling.
"""

from __future__ import annotations

from harlo.intake.questionnaire import (
    IntakeSession,
    detect_disengagement,
    process_answer,
)


class TestSemanticCeiling:
    """Disengagement detection is semantic, not length-based."""

    def test_dismissal_triggers(self) -> None:
        session = IntakeSession()
        assert detect_disengagement("whatever", session) is True
        assert detect_disengagement("skip", session) is True
        assert detect_disengagement("don't care", session) is True
        assert detect_disengagement("idk", session) is True
        assert detect_disengagement("just use defaults", session) is True

    def test_short_substantive_no_trigger(self) -> None:
        """TERSE resilience: short but substantive answers are OK."""
        session = IntakeSession()
        assert detect_disengagement("step by step", session) is False
        assert detect_disengagement("yes", session) is False
        assert detect_disengagement("both", session) is False
        assert detect_disengagement("I prefer analogies", session) is False

    def test_identical_answers_trigger(self) -> None:
        """Identical answers to different questions = disengagement."""
        session = IntakeSession(
            raw_answers={"q1": "same answer", "q2": "same answer"}
        )
        assert detect_disengagement("same answer", session) is True

    def test_different_answers_no_trigger(self) -> None:
        """Different answers are fine."""
        session = IntakeSession(
            raw_answers={"q1": "answer one", "q2": "answer two"}
        )
        assert detect_disengagement("answer three", session) is False

    def test_process_answer_sets_disengaged(self) -> None:
        """process_answer sets user_disengaged on dismissal."""
        session = IntakeSession()
        updated = process_answer(session, "whatever")
        assert updated.user_disengaged is True
        assert not updated.completed

    def test_disengaged_session_returns_no_question(self) -> None:
        """Disengaged session stops returning questions."""
        from harlo.intake.questionnaire import get_next_question
        session = IntakeSession(user_disengaged=True)
        assert get_next_question(session) is None

    def test_answer_length_irrelevant(self) -> None:
        """A one-word answer that's not a dismissal should NOT trigger ceiling."""
        session = IntakeSession()
        assert detect_disengagement("focused", session) is False
        assert detect_disengagement("x", session) is False
        assert detect_disengagement("a", session) is False
