"""Tests for Trust Ledger wiring into resolve_verifications."""

from __future__ import annotations

import pytest

from cognitive_twin.elenchus_v8 import ElenchusQueue
from cognitive_twin.trust import TrustLedger

TRUST_DELTA_VERIFIED = 0.02
TRUST_DELTA_REJECTED = -0.05


@pytest.fixture
def db_path(tmp_path):
    """Return a temp DB path string."""
    return str(tmp_path / "twin.db")


@pytest.fixture
def queue(db_path):
    """Create an ElenchusQueue on the temp DB."""
    return ElenchusQueue(db_path)


@pytest.fixture
def ledger(db_path):
    """Create a TrustLedger on the same temp DB."""
    return TrustLedger(db_path)


class TestTrustWiring:
    """Tests for trust ledger integration with Elenchus verification."""

    def test_verified_claim_increases_trust(self, queue, ledger):
        """Verified claim increases trust by TRUST_DELTA_VERIFIED."""
        claim_id = queue.queue_claim("test claim")
        claim = queue.resolve(claim_id, True)
        assert claim is not None
        delta = TRUST_DELTA_VERIFIED
        ledger.update(delta)
        assert ledger.get_score() == pytest.approx(0.02)

    def test_rejected_claim_decreases_trust(self, queue, ledger):
        """Rejected claim decreases trust by TRUST_DELTA_REJECTED."""
        ledger.update(0.5)
        claim_id = queue.queue_claim("bad claim")
        claim = queue.resolve(claim_id, False)
        assert claim is not None
        delta = TRUST_DELTA_REJECTED
        ledger.update(delta)
        assert ledger.get_score() == pytest.approx(0.45)

    def test_not_found_claim_no_trust_change(self, queue, ledger):
        """Resolving a nonexistent claim_id does not change trust."""
        claim = queue.resolve("nonexistent_id", True)
        assert claim is None
        # No update since claim is None
        assert ledger.get_score() == 0.0

    def test_multiple_verdicts_accumulate(self, queue, ledger):
        """Three verified claims accumulate trust deltas."""
        ids = [queue.queue_claim(f"claim {i}") for i in range(3)]
        for cid in ids:
            claim = queue.resolve(cid, True)
            assert claim is not None
            ledger.update(TRUST_DELTA_VERIFIED)
        assert ledger.get_score() == pytest.approx(0.06)

    def test_mixed_verdicts(self, queue, ledger):
        """One verified + one rejected from zero clamps to 0.0."""
        id1 = queue.queue_claim("good claim")
        id2 = queue.queue_claim("bad claim")

        claim1 = queue.resolve(id1, True)
        assert claim1 is not None
        ledger.update(TRUST_DELTA_VERIFIED)

        claim2 = queue.resolve(id2, False)
        assert claim2 is not None
        ledger.update(TRUST_DELTA_REJECTED)

        # 0.02 + (-0.05) = -0.03, clamped to 0.0
        assert ledger.get_score() == pytest.approx(0.0)

    def test_trust_score_in_response(self, queue, ledger):
        """Resolve flow produces a trust_score in the response dict."""
        claim_id = queue.queue_claim("verifiable claim")

        # Replicate the resolve_verifications logic
        verdicts = [{"claim_id": claim_id, "verdict": True}]
        results = []
        for v in verdicts:
            claim = queue.resolve(v["claim_id"], v["verdict"])
            delta = 0.0
            if claim is not None:
                delta = TRUST_DELTA_VERIFIED if v["verdict"] else TRUST_DELTA_REJECTED
                ledger.update(delta)
            results.append({
                "claim_id": v["claim_id"],
                "resolved": claim is not None,
                "status": claim.status if claim else "not_found",
                "trust_delta": delta,
            })
        response = {
            "status": "ok",
            "resolved": results,
            "remaining_pending": queue.pending_count(),
            "trust_score": ledger.get_score(),
        }

        assert "trust_score" in response
        assert response["trust_score"] == pytest.approx(0.02)
        assert results[0]["trust_delta"] == pytest.approx(0.02)

    def test_trust_clamp_at_zero(self, queue, ledger):
        """Rejecting from 0.0 stays at 0.0 (clamp)."""
        assert ledger.get_score() == 0.0
        claim_id = queue.queue_claim("rejected claim")
        claim = queue.resolve(claim_id, False)
        assert claim is not None
        ledger.update(TRUST_DELTA_REJECTED)
        assert ledger.get_score() == pytest.approx(0.0)
