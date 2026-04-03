"""Gate 2c: Metacognitive routing — Z-score surprise, dual-process, profile-aware.

Tests:
- Z-score computes correctly for known values
- Cold start safety (max(std, 1.0) floor)
- Escalation at threshold
- Rolling stats update (Welford)
- Profile multiplier scales threshold
- No profile → default 2.0, no crash
"""

from __future__ import annotations

import math

from harlo.brainstem.routing import (
    DEFAULT_SURPRISE_THRESHOLD,
    ROLLING_WINDOW,
    compute_surprise,
    get_surprise_threshold,
    route_recall,
    update_rolling_stats,
)
from harlo.usd_lite.prims import (
    CognitiveProfilePrim,
    MultipliersPrim,
    RetrievalPath,
    SessionPrim,
)


class TestComputeSurprise:
    """Z-score surprise computation."""

    def test_zero_surprise(self) -> None:
        """Hamming equals mean → z_score = 0."""
        result = compute_surprise(
            best_hamming=100, rolling_mean=100.0, rolling_std=10.0,
            history_count=50,
        )
        assert result.z_score == 0.0
        assert not result.escalate
        assert result.retrieval_path == RetrievalPath.SYSTEM_1

    def test_positive_surprise(self) -> None:
        """Hamming far above mean → positive z_score."""
        result = compute_surprise(
            best_hamming=200, rolling_mean=100.0, rolling_std=10.0,
            history_count=50,
        )
        assert result.z_score == 10.0
        assert result.escalate
        assert result.retrieval_path == RetrievalPath.SYSTEM_2

    def test_negative_surprise(self) -> None:
        """Hamming below mean → negative z_score, no escalation."""
        result = compute_surprise(
            best_hamming=80, rolling_mean=100.0, rolling_std=10.0,
            history_count=50,
        )
        assert result.z_score < 0
        assert not result.escalate

    def test_threshold_boundary_below(self) -> None:
        """Z-score exactly at threshold → no escalation (not strictly greater)."""
        result = compute_surprise(
            best_hamming=120, rolling_mean=100.0, rolling_std=10.0,
            history_count=50, threshold=2.0,
        )
        assert result.z_score == 2.0
        assert not result.escalate  # Not strictly greater than threshold

    def test_threshold_boundary_above(self) -> None:
        """Z-score just above threshold → escalation."""
        result = compute_surprise(
            best_hamming=121, rolling_mean=100.0, rolling_std=10.0,
            history_count=50, threshold=2.0,
        )
        assert result.z_score > 2.0
        assert result.escalate

    def test_custom_threshold(self) -> None:
        """Custom threshold changes escalation point."""
        result = compute_surprise(
            best_hamming=150, rolling_mean=100.0, rolling_std=10.0,
            history_count=50, threshold=6.0,
        )
        # z_score = 5.0, threshold = 6.0 → no escalation
        assert not result.escalate


class TestColdStart:
    """Cold start safety: max(std, 1.0) prevents blowup."""

    def test_zero_std_floor(self) -> None:
        """std_dev = 0 → floored to 1.0, no division by zero."""
        result = compute_surprise(
            best_hamming=105, rolling_mean=100.0, rolling_std=0.0,
            history_count=3,
        )
        assert result.z_score == 5.0  # (105-100)/1.0
        assert math.isfinite(result.z_score)

    def test_tiny_std_floor(self) -> None:
        """Very small std → floored to 1.0."""
        result = compute_surprise(
            best_hamming=102, rolling_mean=100.0, rolling_std=0.001,
            history_count=5,
        )
        assert result.z_score == 2.0  # (102-100)/1.0, floor applies

    def test_normal_std_no_floor(self) -> None:
        """std > 1.0 → no floor applied."""
        result = compute_surprise(
            best_hamming=120, rolling_mean=100.0, rolling_std=5.0,
            history_count=50,
        )
        assert result.z_score == 4.0  # (120-100)/5.0


class TestRollingStatsUpdate:
    """Welford's algorithm for rolling mean and std update."""

    def test_first_value(self) -> None:
        """First value → mean = value, std = 0."""
        mean, std, count = update_rolling_stats(0.0, 0.0, 0, 100)
        assert mean == 100.0
        assert std == 0.0
        assert count == 1

    def test_second_value(self) -> None:
        """Second value updates correctly."""
        mean, std, count = update_rolling_stats(100.0, 0.0, 1, 200)
        assert count == 2
        assert mean == 150.0
        assert std > 0

    def test_count_capped_at_window(self) -> None:
        """Count never exceeds ROLLING_WINDOW."""
        mean, std, count = update_rolling_stats(100.0, 10.0, 200, 110)
        assert count == ROLLING_WINDOW

    def test_stable_input(self) -> None:
        """Repeated identical values → std converges toward 0."""
        mean, std, count = 100.0, 0.0, 0
        for _ in range(50):
            mean, std, count = update_rolling_stats(mean, std, count, 100)
        assert abs(mean - 100.0) < 1e-6
        assert std < 1.0  # Should be near zero


class TestGetSurpriseThreshold:
    """Profile-aware threshold lookup."""

    def test_no_profile_default(self) -> None:
        """None profile → default 2.0."""
        assert get_surprise_threshold(None) == DEFAULT_SURPRISE_THRESHOLD

    def test_profile_with_custom_threshold(self) -> None:
        """Profile multipliers set custom threshold."""
        profile = CognitiveProfilePrim(
            multipliers=MultipliersPrim(surprise_threshold=2.5),
        )
        assert get_surprise_threshold(profile) == 2.5

    def test_default_profile_matches_default(self) -> None:
        """Default profile has threshold = 2.0 = DEFAULT."""
        profile = CognitiveProfilePrim()
        assert get_surprise_threshold(profile) == DEFAULT_SURPRISE_THRESHOLD


class TestRouteRecall:
    """Full routing pipeline."""

    def test_initial_session(self) -> None:
        """First recall on empty session."""
        session = SessionPrim(current_session_id="s1", exchange_count=0)
        result, updated = route_recall(best_hamming=100, session_prim=session)
        assert updated.exchange_count == 1
        assert updated.surprise_rolling_mean == 100.0
        assert updated.last_query_surprise == result.z_score
        assert updated.last_retrieval_path == result.retrieval_path

    def test_session_updates_after_recall(self) -> None:
        """Session prim updates correctly after recall."""
        session = SessionPrim(
            current_session_id="s1",
            exchange_count=10,
            surprise_rolling_mean=100.0,
            surprise_rolling_std=5.0,
        )
        result, updated = route_recall(best_hamming=110, session_prim=session)
        assert updated.exchange_count == 11
        assert updated.surprise_rolling_mean != 100.0  # Updated
        assert updated.last_retrieval_path in (RetrievalPath.SYSTEM_1, RetrievalPath.SYSTEM_2)

    def test_profile_scales_threshold(self) -> None:
        """High profile threshold prevents escalation."""
        session = SessionPrim(
            current_session_id="s1",
            exchange_count=50,
            surprise_rolling_mean=100.0,
            surprise_rolling_std=5.0,
        )
        high_profile = CognitiveProfilePrim(
            multipliers=MultipliersPrim(surprise_threshold=10.0),
        )
        # z_score ≈ (120-100)/5.0 = 4.0, threshold = 10.0 → no escalation
        result, _ = route_recall(
            best_hamming=120, session_prim=session,
            cognitive_profile=high_profile,
        )
        assert not result.escalate

    def test_low_threshold_escalates(self) -> None:
        """Low profile threshold triggers escalation easily."""
        session = SessionPrim(
            current_session_id="s1",
            exchange_count=50,
            surprise_rolling_mean=100.0,
            surprise_rolling_std=5.0,
        )
        low_profile = CognitiveProfilePrim(
            multipliers=MultipliersPrim(surprise_threshold=0.5),
        )
        result, _ = route_recall(
            best_hamming=105, session_prim=session,
            cognitive_profile=low_profile,
        )
        # z_score ≈ (105-~100)/~5 ≈ 1.0, threshold = 0.5 → escalation
        assert result.escalate

    def test_no_profile_no_crash(self) -> None:
        """Route recall with no profile does not crash."""
        session = SessionPrim(current_session_id="s1", exchange_count=0)
        result, updated = route_recall(best_hamming=50, session_prim=session)
        assert result is not None
        assert updated is not None

    def test_same_query_different_profile_different_route(self) -> None:
        """Same hamming value routes differently with different profiles."""
        session = SessionPrim(
            current_session_id="s1",
            exchange_count=50,
            surprise_rolling_mean=100.0,
            surprise_rolling_std=5.0,
        )
        # Profile with low threshold → escalate
        low = CognitiveProfilePrim(multipliers=MultipliersPrim(surprise_threshold=0.1))
        r_low, _ = route_recall(best_hamming=106, session_prim=session, cognitive_profile=low)

        # Profile with high threshold → no escalate
        high = CognitiveProfilePrim(multipliers=MultipliersPrim(surprise_threshold=99.0))
        r_high, _ = route_recall(best_hamming=106, session_prim=session, cognitive_profile=high)

        assert r_low.escalate
        assert not r_high.escalate
