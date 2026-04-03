"""Hot Store SLA enforcement tests.

Latency SLAs:
- Hot Store write: <2ms (p99, 100 calls)
- Hot Store read (FTS5): <2ms (p99, 100 calls)
"""

from __future__ import annotations

import time

import pytest

from harlo.hot_store import HotStore


@pytest.fixture
def store(tmp_path):
    """Create a HotStore."""
    return HotStore(str(tmp_path / "sla.db"))


class TestHotStoreWriteSLA:
    """SLA: Hot Store write < 2ms p99."""

    def test_store_p99_under_2ms(self, store):
        """100 store calls, p99 < 2ms."""
        times = []
        for i in range(100):
            start = time.perf_counter()
            store.store(f"SLA test message {i}")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        times.sort()
        p99 = times[98]
        assert p99 < 2.0, f"Hot Store write p99 = {p99:.3f}ms (> 2ms SLA)"


class TestHotStoreReadSLA:
    """SLA: Hot Store FTS5 read < 2ms p99."""

    def test_search_p99_under_2ms(self, store):
        """100 search calls after populating, p99 < 2ms."""
        # Populate with 50 traces
        for i in range(50):
            store.store(f"Test message about topic {i} with keywords")

        times = []
        for i in range(100):
            start = time.perf_counter()
            store.search("keywords")
            elapsed = (time.perf_counter() - start) * 1000
            times.append(elapsed)

        times.sort()
        p99 = times[98]
        assert p99 < 2.0, f"Hot Store FTS5 read p99 = {p99:.3f}ms (> 2ms SLA)"
