"""Inquiry Timing — When to surface inquiries.

Determines the appropriate moment to present an inquiry:
- Not during high-load periods
- Not during utility mode
- Respects session boundaries
- Prefers natural conversation pauses
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


# Minimum seconds between surfaced inquiries
MIN_INTERVAL_S = 300.0  # 5 minutes
# Minimum session age before surfacing inquiries (seconds)
MIN_SESSION_AGE_S = 120.0  # 2 minutes
# Max allostatic load for surfacing
MAX_LOAD_FOR_INQUIRY = 0.6


@dataclass
class TimingState:
    """Tracks timing state for inquiry surfacing."""
    session_start: float = field(default_factory=time.time)
    last_surfaced_at: float = 0.0
    utility_mode: bool = False

    def can_surface(
        self,
        allostatic_load: float = 0.0,
        now: float | None = None,
    ) -> bool:
        """Determine if now is an appropriate time to surface an inquiry.

        Checks:
        1. Not in utility mode (S4: mutes DMN)
        2. Session old enough
        3. Sufficient interval since last inquiry
        4. Allostatic load not too high
        """
        if now is None:
            now = time.time()

        # S4: Utility mode mutes DMN entirely
        if self.utility_mode:
            return False

        # Session too young
        if (now - self.session_start) < MIN_SESSION_AGE_S:
            return False

        # Too soon since last inquiry
        if self.last_surfaced_at > 0 and (now - self.last_surfaced_at) < MIN_INTERVAL_S:
            return False

        # System under load
        if allostatic_load > MAX_LOAD_FOR_INQUIRY:
            return False

        return True

    def record_surfaced(self, now: float | None = None) -> None:
        """Record that an inquiry was surfaced."""
        if now is None:
            now = time.time()
        self.last_surfaced_at = now

    def enter_utility_mode(self) -> None:
        """S4: Mute DMN."""
        self.utility_mode = True

    def exit_utility_mode(self) -> None:
        """Exit utility mode, re-enable DMN."""
        self.utility_mode = False
