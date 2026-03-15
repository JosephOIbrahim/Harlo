"""Inquiry Engine — The Twin's voice that asks, not answers.

DMN/Co-Evolution system with safeguards:
- S1: Apophenia guard (evidence-gated)
- S2: Bypass Aletheia truth (tone only, handled by bridge)
- S3: Rupture & repair (rejection tracking)
- S4: Utility mode (mutes DMN)
- S5: Inquiry apoptosis (TTL + decay)
- S7: Trace crystallization
- S8: Sincerity gate
"""

from .types import InquiryType, TTL_HOURS
from .engine import InquiryEngine, Inquiry, InquiryResponse

# Backward-compatible function aliases
synthesize = InquiryEngine.synthesize
prepare_traces_for_dmn = InquiryEngine.prepare_traces_for_dmn

__all__ = [
    "InquiryType",
    "TTL_HOURS",
    "InquiryEngine",
    "Inquiry",
    "InquiryResponse",
    "synthesize",
    "prepare_traces_for_dmn",
]
