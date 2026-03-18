"""Tests for Elenchus v8 deferred verification."""

from __future__ import annotations

import pytest

from cognitive_twin.elenchus_v8 import ElenchusQueue


@pytest.fixture
def queue(tmp_path):
    """Create an ElenchusQueue with temp DB."""
    return ElenchusQueue(str(tmp_path / "elenchus.db"))


class TestQueueClaim:
    """Tests for queue_claim()."""

    def test_queue_returns_claim_id(self, queue):
        """Queueing a claim returns an ID."""
        cid = queue.queue_claim("The user prefers morning work sessions")
        assert len(cid) == 16

    def test_queue_with_explicit_id(self, queue):
        """Explicit claim_id is respected."""
        cid = queue.queue_claim("test claim", claim_id="my-id-001")
        assert cid == "my-id-001"

    def test_queue_with_source_traces(self, queue):
        """Source traces are stored."""
        cid = queue.queue_claim(
            "Pattern detected",
            source_traces=["t1", "t2", "t3"],
            structural_score=0.7,
        )
        pending = queue.get_pending()
        assert len(pending) == 1
        assert pending[0].source_traces == ["t1", "t2", "t3"]
        assert pending[0].structural_score == pytest.approx(0.7)

    def test_queue_status_is_pending(self, queue):
        """New claims have status 'pending'."""
        queue.queue_claim("test")
        pending = queue.get_pending()
        assert pending[0].status == "pending"


class TestGetPending:
    """Tests for get_pending()."""

    def test_empty_queue(self, queue):
        """Empty queue returns empty list."""
        assert queue.get_pending() == []

    def test_oldest_first(self, queue):
        """Pending claims returned oldest first."""
        queue.queue_claim("first", claim_id="c1")
        queue.queue_claim("second", claim_id="c2")
        pending = queue.get_pending()
        assert pending[0].claim_id == "c1"
        assert pending[1].claim_id == "c2"

    def test_respects_limit(self, queue):
        """Limit is respected."""
        for i in range(5):
            queue.queue_claim(f"claim {i}")
        assert len(queue.get_pending(limit=3)) == 3

    def test_excludes_resolved(self, queue):
        """Resolved claims not in pending."""
        cid = queue.queue_claim("will resolve")
        queue.resolve(cid, True)
        assert queue.get_pending() == []


class TestResolve:
    """Tests for resolve()."""

    def test_verify_claim(self, queue):
        """Verified claim moves to 'verified' status."""
        cid = queue.queue_claim("true claim")
        result = queue.resolve(cid, True)
        assert result is not None
        assert result.status == "verified"

    def test_reject_claim(self, queue):
        """Rejected claim moves to 'rejected' status."""
        cid = queue.queue_claim("false claim")
        result = queue.resolve(cid, False)
        assert result is not None
        assert result.status == "rejected"

    def test_resolve_nonexistent(self, queue):
        """Resolving nonexistent claim returns None."""
        result = queue.resolve("nonexistent", True)
        assert result is None

    def test_resolve_already_resolved(self, queue):
        """Resolving already-resolved claim returns None."""
        cid = queue.queue_claim("already done")
        queue.resolve(cid, True)
        result = queue.resolve(cid, False)  # Try to change verdict
        assert result is None

    def test_verified_list(self, queue):
        """get_verified() returns verified claims."""
        c1 = queue.queue_claim("claim 1")
        c2 = queue.queue_claim("claim 2")
        queue.resolve(c1, True)
        queue.resolve(c2, False)

        verified = queue.get_verified()
        rejected = queue.get_rejected()
        assert len(verified) == 1
        assert verified[0].claim_id == c1
        assert len(rejected) == 1
        assert rejected[0].claim_id == c2


class TestPendingCount:
    """Tests for pending_count()."""

    def test_empty(self, queue):
        """Empty queue → 0."""
        assert queue.pending_count() == 0

    def test_increments(self, queue):
        """Count increases with queued claims."""
        queue.queue_claim("a")
        queue.queue_claim("b")
        assert queue.pending_count() == 2

    def test_decrements_on_resolve(self, queue):
        """Count decreases on resolution."""
        cid = queue.queue_claim("test")
        assert queue.pending_count() == 1
        queue.resolve(cid, True)
        assert queue.pending_count() == 0


class TestQueuePersistence:
    """Tests for cross-restart persistence."""

    def test_persists_across_instances(self, tmp_path):
        """Claims survive queue restart."""
        db = str(tmp_path / "persist.db")
        q1 = ElenchusQueue(db)
        cid = q1.queue_claim("persistent claim")

        q2 = ElenchusQueue(db)
        pending = q2.get_pending()
        assert len(pending) == 1
        assert pending[0].claim_id == cid
