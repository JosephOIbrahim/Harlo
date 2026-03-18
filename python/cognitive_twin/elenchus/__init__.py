"""Elenchus Verification Engine — the cognitive immune system.

Public API:
    VerificationState, VerificationResult  — states.py
    verify                                 — verifier.py  (Rule 11: trace-excluded)
    detect_spec_gaming                     — spec_gaming.py (Rule 15)
    extract_intent, check_intent_alignment — intent.py     (Rule 14)
    revise                                 — reviser.py
    run_gvr                                — protocol.py   (Rules 12, 13, 16)
    get_depth                              — depth.py
"""

from .states import VerificationState, VerificationResult
from .verifier import verify
from .spec_gaming import detect_spec_gaming
from .intent import extract_intent, check_intent_alignment
from .reviser import revise
from .protocol import run_gvr
from .depth import get_depth

__all__ = [
    "VerificationState",
    "VerificationResult",
    "verify",
    "detect_spec_gaming",
    "extract_intent",
    "check_intent_alignment",
    "revise",
    "run_gvr",
    "get_depth",
]
