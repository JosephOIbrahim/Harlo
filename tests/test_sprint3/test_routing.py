"""Tests for Sprint 3 Phase 3: Capability routing + OOB consent."""

import pytest

from src.computations.compute_routing import compute_routing
from src.consent import ConsentManager
from src.delegate_claude import HdClaude
from src.delegate_claude_code import HdClaudeCode
from src.delegate_registry import DelegateRegistry
from src.schemas import (
    Burnout,
    BurstPhase,
    CognitiveObservation,
    DynamicsBlock,
    Energy,
    Momentum,
    StateBlock,
)


class TestComputeRouting:
    def test_outputs_requirements_not_delegate_names(self):
        obs = CognitiveObservation()
        prev = StateBlock()
        result = compute_routing(obs, prev)
        assert "expert" in result
        assert "requirements" in result
        reqs = result["requirements"]
        assert "requires_coding" in reqs
        assert "latency_max" in reqs
        assert "context_budget" in reqs
        assert "supported_tasks" in reqs

    def test_frustrated_maps_to_validator(self):
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(frustration_signal=0.9),
        )
        result = compute_routing(obs, StateBlock())
        assert result["expert"] == "frustrated"

    def test_depleted_maps_to_restorer(self):
        obs = CognitiveObservation(
            state=StateBlock(energy=Energy.DEPLETED),
        )
        result = compute_routing(obs, StateBlock())
        assert result["expert"] == "depleted"

    def test_red_always_forces_restorer(self):
        obs = CognitiveObservation(
            state=StateBlock(burnout=Burnout.RED),
            dynamics=DynamicsBlock(frustration_signal=0.0),
        )
        result = compute_routing(obs, StateBlock(), has_valid_consent=True)
        assert result["expert"] == "restorer"
        assert result["requirements"]["requires_coding"] is False

    def test_orange_without_consent_forces_restorer(self):
        obs = CognitiveObservation(
            state=StateBlock(burnout=Burnout.ORANGE),
        )
        result = compute_routing(obs, StateBlock(), has_valid_consent=False)
        assert result["expert"] == "restorer"

    def test_orange_with_consent_allows_override(self):
        obs = CognitiveObservation(
            state=StateBlock(burnout=Burnout.ORANGE),
            dynamics=DynamicsBlock(topic_coherence=0.8),
        )
        result = compute_routing(obs, StateBlock(), has_valid_consent=True)
        assert result["expert"] != "restorer"

    def test_high_momentum_heavy_context(self):
        obs = CognitiveObservation(
            state=StateBlock(momentum=Momentum.ROLLING),
            dynamics=DynamicsBlock(topic_coherence=0.8),
        )
        result = compute_routing(obs, StateBlock())
        assert result["requirements"]["context_budget"] == "heavy"

    def test_burst_requires_realtime(self):
        obs = CognitiveObservation(
            dynamics=DynamicsBlock(
                burst_phase=BurstPhase.PROTECTED,
                topic_coherence=0.9,
                exchange_velocity=0.8,
            ),
        )
        result = compute_routing(obs, StateBlock())
        assert result["requirements"]["latency_max"] == "realtime"

    def test_registry_selects_from_requirements(self):
        reg = DelegateRegistry()
        reg.register(HdClaude())
        reg.register(HdClaudeCode())

        obs = CognitiveObservation(
            dynamics=DynamicsBlock(topic_coherence=0.8),
        )
        result = compute_routing(obs, StateBlock())
        delegate = reg.select(result["requirements"])
        assert delegate.get_delegate_id() == "claude"

    def test_coding_task_routes_to_claude_code(self):
        reg = DelegateRegistry()
        reg.register(HdClaude())
        reg.register(HdClaudeCode())

        result = {
            "requirements": {
                "requires_coding": True,
                "supported_tasks": ["code_generation"],
                "latency_max": "batch",
                "context_budget": "medium",
            }
        }
        delegate = reg.select(result["requirements"])
        assert delegate.get_delegate_id() == "claude_code"


class TestConsentManager:
    def test_grant_and_validate(self):
        cm = ConsentManager()
        token_id = cm.grant_consent("override", current_exchange=5, ttl_exchanges=10)
        assert cm.validate(token_id, current_exchange=10)

    def test_expired_token(self):
        cm = ConsentManager()
        token_id = cm.grant_consent("override", current_exchange=5, ttl_exchanges=3)
        assert cm.validate(token_id, current_exchange=8)
        assert not cm.validate(token_id, current_exchange=9)

    def test_revoked_token(self):
        cm = ConsentManager()
        token_id = cm.grant_consent("override", current_exchange=0)
        cm.revoke(token_id)
        assert not cm.validate(token_id, current_exchange=1)

    def test_invalid_token_id(self):
        cm = ConsentManager()
        assert not cm.validate("nonexistent", current_exchange=0)

    def test_forged_token_rejected(self):
        cm1 = ConsentManager(secret=b"secret1")
        cm2 = ConsentManager(secret=b"secret2")
        token_id = cm1.grant_consent("override", current_exchange=0)
        # cm2 doesn't have the token
        assert not cm2.validate(token_id, current_exchange=1)

    def test_has_valid_consent_scope(self):
        cm = ConsentManager()
        cm.grant_consent("override", current_exchange=0, ttl_exchanges=10)
        assert cm.has_valid_consent("override", current_exchange=5)
        assert not cm.has_valid_consent("other_scope", current_exchange=5)
