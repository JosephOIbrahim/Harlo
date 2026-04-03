"""Gate 4a: Skills observer — incremental, cursor-based, ghost-window safe.

Tests:
- twin_skills returns valid JSON for all 4 query patterns
- Observer tracks last_processed_timestamp cursor
- Processes only new traces (O(new_traces))
- Cursor persisted via to_dict/from_dict
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from harlo.skills.observer import (
    ObserverCursor,
    initial_cursor,
    observe_traces,
    query_skills,
)
from harlo.usd_lite.prims import SkillsContainerPrim, TracePrim


NOW = datetime(2026, 3, 15, 12, 0, 0, tzinfo=timezone.utc)
EARLIER = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 3, 16, 12, 0, 0, tzinfo=timezone.utc)


def _make_trace(tid: str, strength: float = 0.5, accessed: datetime = NOW) -> TracePrim:
    return TracePrim(
        trace_id=tid,
        sdr=[0] * 2048,
        content_hash=f"hash_{tid}",
        strength=strength,
        last_accessed=accessed,
    )


class TestObserveTraces:
    """Incremental observation tests."""

    def test_initial_observation(self) -> None:
        """First run processes all traces."""
        traces = {f"t{i}": _make_trace(f"t{i}") for i in range(10)}
        cursor = initial_cursor()
        skills, new_cursor = observe_traces(traces, SkillsContainerPrim(), cursor)
        assert len(skills.domains) > 0
        assert new_cursor.total_processed == 10

    def test_incremental_only_new_traces(self) -> None:
        """Second run processes only new traces."""
        old_traces = {f"t{i}": _make_trace(f"t{i}", accessed=EARLIER) for i in range(5)}
        cursor = initial_cursor()
        skills, cursor = observe_traces(old_traces, SkillsContainerPrim(), cursor)
        initial_count = cursor.total_processed

        # Add new traces with later timestamp
        new_traces = {**old_traces}
        for i in range(5, 8):
            new_traces[f"t{i}"] = _make_trace(f"t{i}", accessed=LATER)

        skills2, cursor2 = observe_traces(new_traces, skills, cursor)
        # Only 3 new traces should have been processed
        assert cursor2.total_processed == initial_count + 3

    def test_no_new_traces_noop(self) -> None:
        """No new traces → no change."""
        traces = {f"t{i}": _make_trace(f"t{i}") for i in range(5)}
        cursor = initial_cursor()
        skills, cursor = observe_traces(traces, SkillsContainerPrim(), cursor)
        # Same traces, same cursor → no change
        skills2, cursor2 = observe_traces(traces, skills, cursor)
        assert cursor2.total_processed == cursor.total_processed

    def test_cursor_advances(self) -> None:
        """Cursor timestamp advances to latest processed trace."""
        t1 = _make_trace("t1", accessed=EARLIER)
        t2 = _make_trace("t2", accessed=NOW)
        traces = {"t1": t1, "t2": t2}
        cursor = initial_cursor()
        _, new_cursor = observe_traces(traces, SkillsContainerPrim(), cursor)
        assert new_cursor.last_processed_timestamp == NOW

    def test_empty_traces(self) -> None:
        """Empty trace dict → no skills."""
        cursor = initial_cursor()
        skills, new_cursor = observe_traces({}, SkillsContainerPrim(), cursor)
        assert len(skills.domains) == 0

    def test_ghost_window_compliance(self) -> None:
        """100 new traces should complete quickly (< 5s is the budget)."""
        import time
        traces = {f"t{i}": _make_trace(f"t{i}", strength=0.1 * (i % 10)) for i in range(100)}
        cursor = initial_cursor()
        start = time.monotonic()
        skills, _ = observe_traces(traces, SkillsContainerPrim(), cursor)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"Observer took {elapsed:.2f}s for 100 traces (budget: 5s)"


class TestCursorPersistence:
    """Cursor round-trip via to_dict/from_dict."""

    def test_cursor_roundtrip(self) -> None:
        cursor = ObserverCursor(last_processed_timestamp=NOW, total_processed=42)
        restored = ObserverCursor.from_dict(cursor.to_dict())
        assert restored.last_processed_timestamp == NOW
        assert restored.total_processed == 42

    def test_initial_cursor(self) -> None:
        cursor = initial_cursor()
        assert cursor.total_processed == 0


class TestQuerySkills:
    """twin_skills returns valid JSON for all 4 query patterns."""

    def _make_skills(self) -> SkillsContainerPrim:
        from harlo.usd_lite.prims import SkillPrim
        return SkillsContainerPrim(domains={
            "domain_abc1": SkillPrim(
                domain="domain_abc1",
                trace_count=20,
                first_seen=EARLIER,
                last_seen=NOW,
                growth_arc=[0.2, 0.4, 0.6, 0.8],
                hebbian_density=0.3,
            ),
            "domain_xyz9": SkillPrim(
                domain="domain_xyz9",
                trace_count=5,
                first_seen=NOW,
                last_seen=NOW,
                growth_arc=[0.8, 0.6, 0.4],
                hebbian_density=0.1,
            ),
        })

    def test_growing_query(self) -> None:
        result = query_skills(self._make_skills(), "what am I getting better at?")
        assert result["query_type"] == "growing"
        assert isinstance(result["domains"], list)

    def test_gaps_query(self) -> None:
        result = query_skills(self._make_skills(), "what am I avoiding?")
        assert result["query_type"] == "gaps"
        assert isinstance(result["domains"], list)

    def test_depth_query(self) -> None:
        result = query_skills(self._make_skills(), "how deep is my knowledge of domain_abc1?")
        assert result["query_type"] == "depth"

    def test_recommendations_query(self) -> None:
        result = query_skills(self._make_skills(), "what should I work on?")
        assert result["query_type"] == "recommendations"
        assert isinstance(result["domains"], list)

    def test_overview_query(self) -> None:
        result = query_skills(self._make_skills(), "show me everything")
        assert result["query_type"] == "overview"

    def test_empty_skills(self) -> None:
        result = query_skills(SkillsContainerPrim(), "what am I getting better at?")
        assert result["query_type"] == "growing"
        assert len(result["domains"]) == 0
