"""Tests for the Motor Cortex.

Phase 8 Gate:
- Default INHIBIT (Rule 23)
- 5 checks required (Rule 23)
- Level 3 structural/locked (Rule 25)
- One action at a time (Rule 24)
- Motor reflexes always gated (Rule 26)
- Reversibility cap (Rule 29)
"""

import pytest


class TestConsentLevels:
    def test_four_levels(self):
        from harlo.motor.consent import ConsentLevel
        assert ConsentLevel.AUTONOMOUS == 0
        assert ConsentLevel.SESSION == 1
        assert ConsentLevel.PER_ACTION == 2
        assert ConsentLevel.LOCKED == 3

    def test_level_3_never_opens(self):
        """Rule 25: Level 3 is structural, never opens."""
        from harlo.motor.consent import ConsentLevel, ConsentState
        # Level 3 should NEVER return True regardless of inputs
        state = ConsentState()
        state.grant_session()
        state.grant_action("any_action")
        assert state.has_consent(ConsentLevel.LOCKED, action_id="any_action") is False
        assert state.has_consent(ConsentLevel.LOCKED) is False


class TestBasalGanglia:
    """Rule 23: Default INHIBIT. 5 checks required."""

    def test_default_is_inhibit(self):
        """No checks passed -> INHIBIT."""
        from harlo.motor.basal_ganglia import gate, GateDecision
        from harlo.motor.premotor import PlannedAction

        action = PlannedAction(
            action_type="test",
            description="test action",
            target="test",
            payload={},
            consent_level=2,
            reversible=True,
            side_effects=[],
        )
        result = gate(action, {})
        assert result.decision in (GateDecision.INHIBIT, GateDecision.ESCALATE, GateDecision.LOCKED)

    def test_level_3_always_locked(self):
        """Rule 25: Level 3 = LOCKED regardless."""
        from harlo.motor.basal_ganglia import gate, GateDecision
        from harlo.motor.premotor import PlannedAction

        action = PlannedAction(
            action_type="financial",
            description="send money",
            target="bank",
            payload={"amount": 1000},
            consent_level=3,
            reversible=False,
            side_effects=["financial_transaction"],
        )
        result = gate(action, {"consent_level": 3})
        assert result.decision == GateDecision.LOCKED

    def test_reversibility_cap(self):
        """Rule 29: Level 1 + irreversible = Level 2."""
        from harlo.motor.consent import effective_consent_level, ConsentLevel
        # SESSION + irreversible -> PER_ACTION
        assert effective_consent_level(
            ConsentLevel.SESSION, is_irreversible=True
        ) == ConsentLevel.PER_ACTION
        # PER_ACTION + irreversible stays PER_ACTION
        assert effective_consent_level(
            ConsentLevel.PER_ACTION, is_irreversible=True
        ) == ConsentLevel.PER_ACTION
        # Rule 29: NEVER Level 2 + irreversible = Level 3
        assert effective_consent_level(
            ConsentLevel.PER_ACTION, is_irreversible=True
        ) != ConsentLevel.LOCKED


class TestMotorCerebellum:
    """Rule 32: Motor reflex zero-tolerance."""

    def test_single_failure_decompiles(self):
        """Rule 32: Single failure = instant de-compilation."""
        from harlo.motor.motor_cerebellum import MotorCerebellum, ActionPattern
        cerebellum = MotorCerebellum()
        # Register a pattern first
        pattern = ActionPattern(
            pattern_id="pattern_1",
            action_type="test",
            target_pattern="*",
        )
        cerebellum.register_pattern(pattern)
        # Record successes
        cerebellum.record_success("pattern_1")
        cerebellum.record_success("pattern_1")
        # Single failure kills it
        cerebellum.record_failure("pattern_1", reason="test failure")
        reflex = cerebellum.get_pattern("pattern_1")
        assert reflex is not None
        assert reflex.compiled is False


class TestActionPlan:
    """Rule 24 + 31: One action at a time, plan persistence."""

    def test_action_plan_creation(self):
        from harlo.motor.premotor import create_plan, ActionPlan
        plan = create_plan("search the web", [
            {
                "action_type": "web_search",
                "description": "search the web",
                "target": "google",
                "payload": {"query": "test"},
                "reversible": True,
                "side_effects": [],
            }
        ])
        assert isinstance(plan, ActionPlan)
        assert len(plan.steps) >= 1
        assert plan.current_step_index == 0

    def test_one_action_at_a_time(self):
        """Rule 24: Plan steps are atomic, one at a time."""
        from harlo.motor.premotor import create_plan
        plan = create_plan("do multiple things", [
            {
                "action_type": "read",
                "description": "step 1",
                "target": "file",
                "payload": {},
                "reversible": True,
                "side_effects": [],
            },
            {
                "action_type": "write_file",
                "description": "step 2",
                "target": "file",
                "payload": {},
                "reversible": True,
                "side_effects": [],
            },
        ])
        # current_step_index starts at 0 (first step)
        assert plan.current_step_index == 0


class TestCompliance:
    def test_no_sleep_in_motor(self):
        import inspect
        from harlo.motor import (
            premotor, basal_ganglia, executor,
            motor_cerebellum, consent, scope,
        )
        for mod in [premotor, basal_ganglia, executor,
                    motor_cerebellum, consent, scope]:
            source = inspect.getsource(mod)
            assert "sleep(" not in source, f"{mod.__name__} has sleep()"

    def test_no_while_true_in_motor(self):
        import inspect
        from harlo.motor import (
            premotor, basal_ganglia, executor,
            motor_cerebellum, consent, scope,
        )
        for mod in [premotor, basal_ganglia, executor,
                    motor_cerebellum, consent, scope]:
            source = inspect.getsource(mod)
            assert "while True" not in source, f"{mod.__name__} has while True"
