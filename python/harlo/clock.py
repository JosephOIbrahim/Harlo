"""T3 wall-clock — the single canonical source for current wall-time across Harlo.

Per docs/temporal-models.md: T3 = UTC ISO 8601 with microsecond precision and
Z suffix. Use `now_iso()` instead of `datetime.utcnow()` (deprecated) or
`datetime.now()` (local timezone, breaks on non-UTC machines).

Example:
    >>> from harlo.clock import now_iso
    >>> now_iso()
    '2026-05-08T17:53:30.718960Z'
"""

from __future__ import annotations

import datetime


def now_iso() -> str:
    """Return current time as UTC ISO 8601 with microsecond precision and Z suffix.

    Format: 2026-05-08T17:53:30.718960Z

    This is the canonical T3 wall-clock for Harlo. Pinned formatter so all
    persisted wall-clock values match across the codebase.
    """
    return (
        datetime.datetime.now(datetime.UTC)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )
