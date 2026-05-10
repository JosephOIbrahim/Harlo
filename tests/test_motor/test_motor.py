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

    def test_decompile_resets_success_count(self):
        """Rule 32 literal: de-compilation MUST set success_count=0."""
        from harlo.motor.motor_cerebellum import MotorCerebellum, ActionPattern
        cerebellum = MotorCerebellum()
        cerebellum.register_pattern(ActionPattern(
            pattern_id="p", action_type="t", target_pattern="*",
        ))
        for _ in range(5):
            cerebellum.record_success("p")
        assert cerebellum.get_pattern("p").success_count == 5
        cerebellum.record_failure("p", reason="boom")
        reflex = cerebellum.get_pattern("p")
        assert reflex.compiled is False
        assert reflex.success_count == 0

    def test_decompile_listener_sees_prior_success_count(self):
        """on_decompile fires BEFORE the Rule 32 reset so audit captures prior."""
        from harlo.motor.motor_cerebellum import MotorCerebellum, ActionPattern
        seen: list[int] = []
        cerebellum = MotorCerebellum(
            on_decompile=lambda p, r: seen.append(p.success_count)
        )
        cerebellum.register_pattern(ActionPattern(
            pattern_id="p", action_type="t", target_pattern="*",
            success_count=42,
        ))
        cerebellum.record_failure("p", reason="boom")
        # Listener observed the pre-reset count (Rule 32 audit trail).
        assert seen == [42]
        # External readers see the reset (Rule 32 literal).
        assert cerebellum.get_pattern("p").success_count == 0

    def test_decompile_fires_observer_hook(self):
        """Decompile events must be observable to higher layers."""
        from harlo.motor.motor_cerebellum import MotorCerebellum, ActionPattern
        observed: list[tuple[str, str]] = []
        cerebellum = MotorCerebellum(
            on_decompile=lambda p, r: observed.append((p.pattern_id, r))
        )
        cerebellum.register_pattern(ActionPattern(
            pattern_id="p", action_type="t", target_pattern="*",
        ))
        cerebellum.record_failure("p", reason="transient downstream error")
        assert observed == [("p", "transient downstream error")]

    def test_decompile_isolates_listener_errors(self):
        """A raising on_decompile listener must NOT abort record_failure."""
        from harlo.motor.motor_cerebellum import MotorCerebellum, ActionPattern

        def boom(_pattern, _reason):
            raise RuntimeError("listener exploded")

        cerebellum = MotorCerebellum(on_decompile=boom)
        cerebellum.register_pattern(ActionPattern(
            pattern_id="p", action_type="t", target_pattern="*",
        ))
        # Must not raise: listener errors are fire-and-forget.
        cerebellum.record_failure("p", reason="downstream")
        reflex = cerebellum.get_pattern("p")
        # Decompilation bookkeeping completed despite the listener exception.
        assert reflex.compiled is False
        assert reflex.success_count == 0
        assert reflex.decompile_reason == "downstream"


class TestExecutorSnapshot:
    """TOCTOU defence: gate decision and handler must see the same state."""

    @pytest.fixture(autouse=True)
    def _isolate(self, monkeypatch):
        # Stub the gate to a pass-through so this test exercises ONLY snapshot
        # semantics, not the live Basal Ganglia policy.  The gate has 5 checks
        # and adding a 6th in the future would silently break a test that
        # actually intends to verify snapshot isolation.
        from harlo.motor import executor as _exec
        from harlo.motor.basal_ganglia import GateDecision, GateResult

        monkeypatch.setattr(
            _exec, "gate",
            lambda action, state, consent=None: GateResult(
                decision=GateDecision.DISINHIBIT,
            ),
        )
        yield
        # Clean up the module-level _HANDLERS dict to avoid cross-test leakage.
        _exec._HANDLERS.pop("snapshot_test", None)

    def test_session_state_snapshot_isolation(self):
        """Mutations to session_state during handler must not race the gate."""
        from harlo.motor.executor import (
            execute_one, register_handler, ExecutionStatus,
        )
        from harlo.motor.premotor import PlannedAction

        live_state = {"cognitive_state": "GREEN", "consent_level": 0}
        seen: dict = {}

        def recording_handler(action, session_state):
            # Capture what the handler observes; then mutate the *original*
            # dict to simulate a concurrent flip.  The snapshot must keep the
            # handler's view stable.
            seen["handler_state"] = dict(session_state)
            live_state["cognitive_state"] = "RED"
            return {"ok": True}

        register_handler("snapshot_test", recording_handler)
        action = PlannedAction(
            action_type="snapshot_test",
            description="snapshot probe",
            target="probe",
            payload={},
            consent_level=0,   # AUTONOMOUS
            reversible=True,
            side_effects=[],
        )
        result = execute_one(action, live_state)
        assert result.status == ExecutionStatus.SUCCESS
        # The handler's view was the snapshot, not the post-mutation state.
        assert seen["handler_state"]["cognitive_state"] == "GREEN"


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
