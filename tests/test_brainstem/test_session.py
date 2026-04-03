"""Session prim update tests after recall operations."""

from __future__ import annotations

from harlo.brainstem.session_updater import update_session_after_recall
from harlo.usd_lite.prims import (
    CognitiveProfilePrim,
    MultipliersPrim,
    RetrievalPath,
    SessionPrim,
)


class TestUpdateSessionAfterRecall:
    """Session prim updates correctly after recall."""

    def test_initial_recall(self) -> None:
        """First recall sets initial values."""
        session = SessionPrim(current_session_id="s1", exchange_count=0)
        updated, result = update_session_after_recall(session, best_hamming=100)
        assert updated.exchange_count == 1
        assert updated.surprise_rolling_mean == 100.0
        assert updated.current_session_id == "s1"

    def test_mean_changes(self) -> None:
        """Mean updates after recall."""
        session = SessionPrim(
            current_session_id="s1",
            exchange_count=10,
            surprise_rolling_mean=100.0,
            surprise_rolling_std=5.0,
        )
        updated, _ = update_session_after_recall(session, best_hamming=200)
        assert updated.surprise_rolling_mean != 100.0

    def test_z_score_stored(self) -> None:
        """last_query_surprise reflects Z-score."""
        session = SessionPrim(
            current_session_id="s1",
            exchange_count=10,
            surprise_rolling_mean=100.0,
            surprise_rolling_std=5.0,
        )
        updated, result = update_session_after_recall(session, best_hamming=120)
        assert updated.last_query_surprise == result.z_score

    def test_retrieval_path_stored(self) -> None:
        """last_retrieval_path reflects routing decision."""
        session = SessionPrim(
            current_session_id="s1",
            exchange_count=50,
            surprise_rolling_mean=100.0,
            surprise_rolling_std=5.0,
        )
        updated, result = update_session_after_recall(session, best_hamming=100)
        assert updated.last_retrieval_path == result.retrieval_path

    def test_with_cognitive_profile(self) -> None:
        """Profile is passed through to routing."""
        session = SessionPrim(current_session_id="s1", exchange_count=0)
        profile = CognitiveProfilePrim(
            multipliers=MultipliersPrim(surprise_threshold=99.0),
        )
        updated, result = update_session_after_recall(
            session, best_hamming=500, cognitive_profile=profile,
        )
        # With threshold 99.0, even a very high hamming shouldn't escalate
        assert not result.escalate

    def test_without_cognitive_profile(self) -> None:
        """No profile → uses default threshold, no crash."""
        session = SessionPrim(current_session_id="s1", exchange_count=0)
        updated, result = update_session_after_recall(session, best_hamming=100)
        assert result is not None
        assert updated is not None
