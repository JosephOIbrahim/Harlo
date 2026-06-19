"""Phase 4 read path — biometric Energy seed at session init.

seed_block() reads today's persisted biometric_prior, classifies it against the
rolling 14-day baseline, and returns the Energy seed that twin_session_status
surfaces. Absent prior → None (session startup unchanged; default MEDIUM as
today). A missing prior must NEVER block startup — callers wrap defensively.

This read path backs BOTH surfaces: twin_session_status's biometric_seed block,
and the engine's DEEP seed (CognitiveEngine seeds a new session's first-exchange
resolved Energy from this, gated by BIOMETRICS_ENABLED).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from .baseline import compute_baseline
from .mapping import classify


def seed_block(today: Optional[str] = None, store=None) -> Optional[dict]:
    """The biometric Energy seed for `today` (default: system date), or None if
    no prior was captured for that date."""
    today = today or date.today().isoformat()
    if store is None:
        from .persistence import default_store

        store = default_store(with_stage=False)  # read path → buffer only
    prior = store.today_prior(today)
    if prior is None:
        return None
    # Baseline = the rolling window of PRIOR days (today excluded). Median is
    # order-independent, so the newest-first list is fine.
    window = [p for p in store.recent_priors(15) if p.calendar_date != today][:14]
    verdict = classify(prior, compute_baseline(window))
    return {
        "date": today,
        "capacity": verdict.capacity.value,
        "energy": verdict.energy_seed.name,
        "directive_mode": verdict.directive_mode,
        "source": prior.source,
        "pre_baseline": verdict.pre_baseline,
    }
