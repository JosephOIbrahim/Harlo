"""Rupture & Repair — S3: Rejection handling.

Rejection = permanent trace (weight 2.0).
3 rejections on same topic -> offer to stop asking.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


REJECTION_WEIGHT = 2.0
REJECTION_LIMIT = 3


@dataclass
class RejectionTrace:
    """A permanent record of an inquiry rejection."""
    inquiry_id: str
    topic_key: str
    timestamp: float
    weight: float = REJECTION_WEIGHT
    response_text: str = ""


@dataclass
class RuptureLedger:
    """Tracks rejections per topic for rupture-repair logic.

    Permanent traces are never deleted. They inform future inquiry
    decisions and carry weight 2.0 in relevance scoring.
    """
    traces: list[RejectionTrace] = field(default_factory=list)
    _topic_counts: dict[str, int] = field(default_factory=dict)

    def record_rejection(
        self,
        inquiry_id: str,
        topic_key: str,
        response_text: str = "",
        ts: float | None = None,
    ) -> RejectionTrace:
        """Record a rejection. Returns the trace."""
        if ts is None:
            ts = time.time()

        trace = RejectionTrace(
            inquiry_id=inquiry_id,
            topic_key=topic_key,
            timestamp=ts,
            response_text=response_text,
        )
        self.traces.append(trace)
        self._topic_counts[topic_key] = self._topic_counts.get(topic_key, 0) + 1
        return trace

    def rejection_count(self, topic_key: str) -> int:
        """Get number of rejections for a topic."""
        return self._topic_counts.get(topic_key, 0)

    def should_offer_stop(self, topic_key: str) -> bool:
        """S3: 3 rejections on same topic -> offer to stop."""
        return self.rejection_count(topic_key) >= REJECTION_LIMIT

    def topic_weight(self, topic_key: str) -> float:
        """Total rejection weight for a topic."""
        return self.rejection_count(topic_key) * REJECTION_WEIGHT

    def is_topic_blocked(self, topic_key: str) -> bool:
        """Check if a topic has been explicitly blocked after offer-to-stop."""
        # After 3 rejections and the stop offer, the topic is suppressed
        # unless explicitly re-enabled via consent module
        return self.rejection_count(topic_key) >= REJECTION_LIMIT

    def get_all_rejected_topics(self) -> list[str]:
        """Return topic keys that have reached the rejection limit."""
        return [
            k for k, v in self._topic_counts.items()
            if v >= REJECTION_LIMIT
        ]
