"""Coach Core projection SLA enforcement tests.

SLA: Coach Core projection < 10ms.
"""

from __future__ import annotations

import time

import pytest

from cognitive_twin.hot_store import HotStore
from cognitive_twin.coach import project_coach


@pytest.fixture
def populated_db(tmp_path):
    """DB with some data for projection."""
    db = str(tmp_path / "coach_sla.db")
    store = HotStore(db)
    for i in range(10):
        store.store(f"Trace {i} about topic {i}", domain="test")
    return db


class TestCoachSLA:
    """SLA: Coach Core projection < 10ms."""

    def test_projection_under_10ms(self, populated_db):
        """100 projection calls, p99 < 10ms."""
        times = []
        for _ in range(100):
            start = time.perf_counter()
            project_coach(populated_db)
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        times.sort()
        p99 = times[98]
        assert p99 < 10.0, f"Coach projection p99 = {p99:.3f}ms (> 10ms SLA)"
