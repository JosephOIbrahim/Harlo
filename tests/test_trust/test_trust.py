"""Tests for Trust Ledger."""

from __future__ import annotations

import pytest

from cognitive_twin.trust import TrustLedger, TIER_FAMILIAR, TIER_TRUSTED


@pytest.fixture
def ledger(tmp_path):
    """Create a TrustLedger with temp DB."""
    return TrustLedger(str(tmp_path / "trust.db"))


class TestTrustInit:
    """Tests for initial trust state."""

    def test_new_user_score_zero(self, ledger):
        """New user starts at 0.0."""
        assert ledger.get_score() == 0.0

    def test_new_user_tier_new(self, ledger):
        """New user is in 'new' tier."""
        assert ledger.get_tier() == "new"


class TestTrustUpdate:
    """Tests for trust score updates."""

    def test_positive_update(self, ledger):
        """Positive delta increases score."""
        result = ledger.update(0.1)
        assert result == pytest.approx(0.1)
        assert ledger.get_score() == pytest.approx(0.1)

    def test_negative_update(self, ledger):
        """Negative delta decreases score."""
        ledger.update(0.5)
        result = ledger.update(-0.2)
        assert result == pytest.approx(0.3)

    def test_clamp_upper(self, ledger):
        """Score clamped to 1.0."""
        result = ledger.update(5.0)
        assert result == 1.0

    def test_clamp_lower(self, ledger):
        """Score clamped to 0.0."""
        result = ledger.update(-5.0)
        assert result == 0.0

    def test_continuous_updates(self, ledger):
        """Multiple small updates accumulate."""
        for _ in range(10):
            ledger.update(0.05)
        assert ledger.get_score() == pytest.approx(0.5)

    def test_update_idempotent_state(self, ledger):
        """Update with 0 delta doesn't change score."""
        ledger.update(0.5)
        result = ledger.update(0.0)
        assert result == pytest.approx(0.5)


class TestTrustTiers:
    """Tests for tier classification."""

    def test_tier_new(self, ledger):
        """Score < 0.3 → 'new'."""
        ledger.update(0.2)
        assert ledger.get_tier() == "new"

    def test_tier_familiar(self, ledger):
        """0.3 <= score < 0.7 → 'familiar'."""
        ledger.update(0.5)
        assert ledger.get_tier() == "familiar"

    def test_tier_trusted(self, ledger):
        """Score >= 0.7 → 'trusted'."""
        ledger.update(0.8)
        assert ledger.get_tier() == "trusted"

    def test_tier_boundary_familiar(self, ledger):
        """Exact 0.3 → 'familiar'."""
        ledger.update(0.3)
        assert ledger.get_tier() == "familiar"

    def test_tier_boundary_trusted(self, ledger):
        """Exact 0.7 → 'trusted'."""
        ledger.update(0.7)
        assert ledger.get_tier() == "trusted"


class TestTrustReset:
    """Tests for trust reset."""

    def test_reset_to_zero(self, ledger):
        """Reset brings score back to 0.0."""
        ledger.update(0.8)
        result = ledger.reset()
        assert result == pytest.approx(0.0)
        assert ledger.get_score() == pytest.approx(0.0)

    def test_reset_idempotent(self, ledger):
        """Resetting twice is fine."""
        ledger.reset()
        ledger.reset()
        assert ledger.get_score() == pytest.approx(0.0)


class TestTrustMultiUser:
    """Tests for multi-user support."""

    def test_separate_users(self, ledger):
        """Different users have independent scores."""
        ledger.update(0.5, user_id="alice")
        ledger.update(0.3, user_id="bob")
        assert ledger.get_score("alice") == pytest.approx(0.5)
        assert ledger.get_score("bob") == pytest.approx(0.3)
