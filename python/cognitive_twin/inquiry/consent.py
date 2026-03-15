"""Consent & Boundary Management for inquiries.

Manages user consent for inquiry topics and types.
Integrates with rupture_repair for rejection-based blocking.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .types import InquiryType


@dataclass
class ConsentRecord:
    """A consent decision for a topic or inquiry type."""
    key: str  # topic_key or InquiryType.value
    allowed: bool
    set_at: float = field(default_factory=time.time)
    reason: str = ""


@dataclass
class ConsentManager:
    """Manages user consent boundaries for inquiries.

    Defaults to opt-in: inquiries are allowed unless explicitly blocked.
    Blocked topics from rupture_repair (3+ rejections) are auto-blocked
    but can be re-enabled here.
    """
    records: dict[str, ConsentRecord] = field(default_factory=dict)
    globally_enabled: bool = True

    def set_consent(
        self,
        key: str,
        allowed: bool,
        reason: str = "",
        ts: float | None = None,
    ) -> ConsentRecord:
        """Set consent for a key (topic or inquiry type)."""
        if ts is None:
            ts = time.time()
        record = ConsentRecord(key=key, allowed=allowed, set_at=ts, reason=reason)
        self.records[key] = record
        return record

    def is_allowed(self, key: str) -> bool:
        """Check if a key is allowed. Default: True."""
        if not self.globally_enabled:
            return False
        record = self.records.get(key)
        if record is None:
            return True  # Opt-in default
        return record.allowed

    def is_type_allowed(self, inquiry_type: InquiryType) -> bool:
        """Check if an inquiry type is allowed."""
        return self.is_allowed(inquiry_type.value)

    def block_topic(self, topic_key: str, reason: str = "user_request") -> ConsentRecord:
        """Block a specific topic."""
        return self.set_consent(topic_key, allowed=False, reason=reason)

    def unblock_topic(self, topic_key: str, reason: str = "user_request") -> ConsentRecord:
        """Unblock a previously blocked topic."""
        return self.set_consent(topic_key, allowed=True, reason=reason)

    def disable_all(self, reason: str = "user_request") -> None:
        """Globally disable all inquiries."""
        self.globally_enabled = False

    def enable_all(self, reason: str = "user_request") -> None:
        """Re-enable inquiries globally."""
        self.globally_enabled = True

    def get_blocked_keys(self) -> list[str]:
        """Return all explicitly blocked keys."""
        return [k for k, r in self.records.items() if not r.allowed]
