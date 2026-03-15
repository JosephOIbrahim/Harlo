"""Bridge Protocol — escalation, amygdala, consolidation, integrity, intent, bypass, reflex compiler."""

from .escalation import should_escalate, escalate
from .amygdala import is_amygdala_trigger, create_amygdala_reflex
from .consolidation import consolidate_resolution
from .integrity import verify_merkle_root
from .intent_check import check_intent_preserved
from .epistemological_bypass import should_bypass_aletheia, emit_perception_gap, accept_blind_spot
from .reflex_compiler import compile_to_reflex

__all__ = [
    "should_escalate",
    "escalate",
    "is_amygdala_trigger",
    "create_amygdala_reflex",
    "consolidate_resolution",
    "verify_merkle_root",
    "check_intent_preserved",
    "should_bypass_aletheia",
    "emit_perception_gap",
    "accept_blind_spot",
    "compile_to_reflex",
]
