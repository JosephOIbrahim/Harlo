"""Tests for cognitive recalibration."""

from __future__ import annotations

import pytest

from harlo.trust import TrustLedger
from harlo.trust.recalibration import (
    trigger_recalibration,
    is_intake_complete,
    ensure_profile_schema,
)


@pytest.fixture
def db_path(tmp_path):
    """Temporary database path."""
    return str(tmp_path / "recal.db")


class TestTriggerRecalibration:
    """Tests for trigger_recalibration()."""

    def test_resets_trust(self, db_path):
        """Recalibration resets trust to 0.0."""
        ledger = TrustLedger(db_path)
        ledger.update(0.8)
        assert ledger.get_score() == pytest.approx(0.8)

        result = trigger_recalibration(db_path)

        assert result["status"] == "recalibrated"
        assert result["trust_score"] == 0.0
        assert ledger.get_score() == pytest.approx(0.0)

    def test_clears_intake_flag(self, db_path):
        """Recalibration sets intake_complete to False."""
        ensure_profile_schema(db_path)

        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO cognitive_profile (user_id, intake_complete, profile_json, last_calibrated) "
            "VALUES ('default', 1, '{\"test\": true}', 0.0)"
        )
        conn.commit()
        conn.close()

        assert is_intake_complete(db_path) is True

        trigger_recalibration(db_path)

        assert is_intake_complete(db_path) is False

    def test_clears_profile_json(self, db_path):
        """Recalibration clears the profile JSON."""
        ensure_profile_schema(db_path)

        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO cognitive_profile (user_id, intake_complete, profile_json, last_calibrated) "
            "VALUES ('default', 1, '{\"detailed\": \"profile\"}', 0.0)"
        )
        conn.commit()
        conn.close()

        trigger_recalibration(db_path)

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT profile_json FROM cognitive_profile WHERE user_id = 'default'"
        ).fetchone()
        conn.close()

        assert row[0] == "{}"

    def test_idempotent(self, db_path):
        """Calling recalibration twice is safe."""
        r1 = trigger_recalibration(db_path)
        r2 = trigger_recalibration(db_path)
        assert r1["status"] == "recalibrated"
        assert r2["status"] == "recalibrated"
        assert r2["trust_score"] == 0.0

    def test_returns_correct_user_id(self, db_path):
        """Result includes the user_id."""
        result = trigger_recalibration(db_path, user_id="joe")
        assert result["user_id"] == "joe"


class TestIsIntakeComplete:
    """Tests for is_intake_complete()."""

    def test_no_profile_returns_false(self, db_path):
        """No profile entry → False."""
        assert is_intake_complete(db_path) is False

    def test_complete_returns_true(self, db_path):
        """intake_complete=1 → True."""
        ensure_profile_schema(db_path)

        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO cognitive_profile (user_id, intake_complete, profile_json, last_calibrated) "
            "VALUES ('default', 1, '{}', 0.0)"
        )
        conn.commit()
        conn.close()

        assert is_intake_complete(db_path) is True
