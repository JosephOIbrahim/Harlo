"""Inquiry types and TTL configuration.

Five inquiry categories the Twin's DMN can generate.
TTL values per spec S5.
"""

from __future__ import annotations

from enum import Enum


class InquiryType(Enum):
    PATTERN = "pattern"              # Behavioral patterns
    CONTRADICTION = "contradiction"  # Self-contradictions
    DRIFT = "drift"                  # Value/priority drift
    GROWTH = "growth"                # Growth edge detection
    EXISTENTIAL = "existential"      # Deep meaning questions


TTL_HOURS: dict[InquiryType, int] = {
    InquiryType.PATTERN: 72,          # 3 days
    InquiryType.CONTRADICTION: 48,    # 2 days
    InquiryType.DRIFT: 336,           # 14 days
    InquiryType.GROWTH: 336,          # 14 days
    InquiryType.EXISTENTIAL: 720,     # 30 days
}

# S1: Minimum evidence counts per depth level
EVIDENCE_THRESHOLDS: dict[int, int] = {
    1: 5,
    2: 8,
    3: 15,
    4: 25,
}
