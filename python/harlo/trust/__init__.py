"""Trust Ledger — continuous [0.0, 1.0] trust score.

Basal Ganglia evaluates the float directly for behavior gating:
- 0.0–0.3: New — passive store only
- 0.3–0.7: Familiar — context/pattern surfacing
- 0.7–1.0: Trusted — proactive coaching/pushback
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Tier thresholds
TIER_FAMILIAR = 0.3
TIER_TRUSTED = 0.7


class TrustLedger:
    """Manages the continuous trust score for a user.

    Trust score is a float in [0.0, 1.0] that determines behavior
    gating via the Basal Ganglia. Updates are smooth and continuous.
    """

    def __init__(self, db_path: str) -> None:
        """Initialize TrustLedger.

        Args:
            db_path: Path to SQLite database file.
        """
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trust_ledger (
                user_id TEXT PRIMARY KEY,
                trust_score REAL NOT NULL DEFAULT 0.0,
                last_updated REAL NOT NULL
            )
        """)
        conn.commit()
        conn.close()

    def get_score(self, user_id: str = "default") -> float:
        """Get current trust score for a user.

        Args:
            user_id: User identifier (default: "default").

        Returns:
            Trust score in [0.0, 1.0]. Returns 0.0 for new users.
        """
        conn = sqlite3.connect(self._db_path)
        try:
            row = conn.execute(
                "SELECT trust_score FROM trust_ledger WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            return row[0] if row else 0.0
        finally:
            conn.close()

    def update(self, delta: float, user_id: str = "default") -> float:
        """Update trust score by delta, clamped to [0.0, 1.0].

        Args:
            delta: Amount to add (positive or negative).
            user_id: User identifier.

        Returns:
            New trust score after update.
        """
        conn = sqlite3.connect(self._db_path)
        try:
            current = self.get_score(user_id)
            new_score = max(0.0, min(1.0, current + delta))
            now = time.time()

            conn.execute(
                """INSERT INTO trust_ledger (user_id, trust_score, last_updated)
                   VALUES (?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       trust_score = excluded.trust_score,
                       last_updated = excluded.last_updated""",
                (user_id, new_score, now),
            )
            conn.commit()
            return new_score
        finally:
            conn.close()

    def reset(self, user_id: str = "default") -> float:
        """Reset trust score to 0.0.

        Args:
            user_id: User identifier.

        Returns:
            0.0
        """
        return self.update(-self.get_score(user_id), user_id)

    def get_tier(self, user_id: str = "default") -> str:
        """Get trust tier name for a user.

        Args:
            user_id: User identifier.

        Returns:
            One of "new", "familiar", "trusted".
        """
        score = self.get_score(user_id)
        if score >= TIER_TRUSTED:
            return "trusted"
        elif score >= TIER_FAMILIAR:
            return "familiar"
        return "new"
