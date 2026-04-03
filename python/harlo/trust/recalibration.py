"""Cognitive recalibration — reset intake and trust.

trigger_cognitive_recalibration resets the user's cognitive profile,
allowing re-intake when major life/role changes occur.
"""

from __future__ import annotations

import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def ensure_profile_schema(db_path: str) -> None:
    """Ensure the cognitive_profile table exists.

    Args:
        db_path: Path to SQLite database.
    """
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cognitive_profile (
                user_id TEXT PRIMARY KEY,
                intake_complete INTEGER NOT NULL DEFAULT 0,
                profile_json TEXT NOT NULL DEFAULT '{}',
                last_calibrated REAL NOT NULL DEFAULT 0.0
            )
        """)
        conn.commit()
    finally:
        conn.close()


def trigger_recalibration(db_path: str, user_id: str = "default") -> dict:
    """Reset cognitive profile and trust for re-intake.

    Clears the cognitive profile and resets intake_complete to false.
    Also resets trust score to 0.0.

    Args:
        db_path: Path to SQLite database.
        user_id: User identifier.

    Returns:
        Dict with status and reset details.
    """
    ensure_profile_schema(db_path)

    conn = sqlite3.connect(db_path)
    try:
        now = time.time()

        # Clear cognitive profile
        conn.execute(
            """INSERT INTO cognitive_profile (user_id, intake_complete, profile_json, last_calibrated)
               VALUES (?, 0, '{}', ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   intake_complete = 0,
                   profile_json = '{}',
                   last_calibrated = excluded.last_calibrated""",
            (user_id, now),
        )
        conn.commit()
    finally:
        conn.close()

    # Reset trust score
    from harlo.trust import TrustLedger

    ledger = TrustLedger(db_path)
    ledger.reset(user_id)

    logger.info("Cognitive recalibration triggered for user=%s", user_id)

    return {
        "status": "recalibrated",
        "user_id": user_id,
        "intake_complete": False,
        "trust_score": 0.0,
    }


def is_intake_complete(db_path: str, user_id: str = "default") -> bool:
    """Check if cognitive intake is complete for a user.

    Args:
        db_path: Path to SQLite database.
        user_id: User identifier.

    Returns:
        True if intake is complete.
    """
    ensure_profile_schema(db_path)

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT intake_complete FROM cognitive_profile WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        return bool(row[0]) if row else False
    finally:
        conn.close()
