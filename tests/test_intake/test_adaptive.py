"""Gate 4e: Intake questionnaire — adaptive administration."""

from __future__ import annotations

from cognitive_twin.intake.questionnaire import (
    QUESTION_BANK,
    IntakeSession,
    get_next_question,
    process_answer,
    score_answer,
)


class TestQuestionBank:
    """Question bank is well-formed."""

    def test_has_questions(self) -> None:
        assert len(QUESTION_BANK) >= 5

    def test_questions_have_required_fields(self) -> None:
        for q in QUESTION_BANK:
            assert q.question_id
            assert q.dimension
            assert q.text
            assert len(q.anchors) == 2

    def test_all_dimensions_covered(self) -> None:
        dims = {q.dimension for q in QUESTION_BANK}
        assert "associativity" in dims
        assert "detail" in dims
        assert "attention" in dims
        assert "stress" in dims


class TestAdaptiveFlow:
    """Intake questionnaire flows correctly."""

    def test_initial_session(self) -> None:
        session = IntakeSession()
        assert session.current_index == 0
        assert not session.completed
        assert not session.user_disengaged

    def test_get_first_question(self) -> None:
        session = IntakeSession()
        q = get_next_question(session)
        assert q is not None
        assert q.question_id == QUESTION_BANK[0].question_id

    def test_process_answer_advances(self) -> None:
        session = IntakeSession()
        updated = process_answer(session, "I connect to many concepts")
        assert updated.current_index == 1
        assert len(updated.answers) == 1

    def test_full_intake_completes(self) -> None:
        session = IntakeSession()
        answers = [
            "I connect to many concepts",
            "I focus on specific details",
            "I work in sustained deep focus sessions",
            "My thinking becomes sharper under pressure",
            "I prefer analogies and metaphors",
            "I like to see the big picture first",
        ]
        for i in range(len(QUESTION_BANK)):
            q = get_next_question(session)
            assert q is not None, f"Question {i} should be available"
            session = process_answer(session, answers[i])
        assert session.completed

    def test_completed_session_returns_none(self) -> None:
        session = IntakeSession(completed=True)
        assert get_next_question(session) is None

    def test_session_roundtrip(self) -> None:
        session = IntakeSession(current_index=2, answers={"q1_assoc": 0.7})
        restored = IntakeSession.from_dict(session.to_dict())
        assert restored.current_index == 2
        assert restored.answers["q1_assoc"] == 0.7
