"""Tests for schedule modulation in src/computations/compute_routing.py.

Schedule overrides mirror the burnout safety pattern: FAMILY forces restorer
(consent-ignored), OFF_HOURS lightens context, WORK is normal.
"""

from __future__ import annotations

import pytest

from src.computations.compute_routing import compute_routing
from src.schemas import (
    Burnout,
    BurstPhase,
    CognitiveObservation,
    DynamicsBlock,
    Energy,
    Momentum,
    ScheduleBlock,
    ScheduleKind,
    StateBlock,
)


@pytest.fixture
def base_state() -> StateBlock:
    return StateBlock(
        momentum=Momentum.BUILDING,
        burnout=Burnout.GREEN,
        energy=Energy.MEDIUM,
    )


@pytest.fixture
def base_dynamics() -> DynamicsBlock:
    return DynamicsBlock(
        exchange_velocity=0.7,
        topic_coherence=0.8,
        tasks_completed=2,
    )


def _make_obs(state, dynamics, schedule_kind, override_reason=""):
    return CognitiveObservation(
        state=state,
        dynamics=dynamics,
        schedule=ScheduleBlock(kind=schedule_kind, override_reason=override_reason),
    )


class TestWork:
    def test_work_normal_routing(self, base_state, base_dynamics):
        obs = _make_obs(base_state, base_dynamics, ScheduleKind.WORK)
        result = compute_routing(obs, base_state)
        assert result["schedule_state"] == "WORK"
        assert result["expert"] != "restorer"
        assert result["requirements"]["context_budget"] in ("medium", "heavy", "light")

    def test_work_does_not_force_coaching_only(self, base_state, base_dynamics):
        obs = _make_obs(base_state, base_dynamics, ScheduleKind.WORK)
        result = compute_routing(obs, base_state)
        assert "coaching" in result["requirements"]["supported_tasks"] or \
               "reasoning" in result["requirements"]["supported_tasks"]


class TestOffHours:
    def test_off_hours_sets_light_context(self, base_state, base_dynamics):
        obs = _make_obs(base_state, base_dynamics, ScheduleKind.OFF_HOURS)
        result = compute_routing(obs, base_state)
        assert result["schedule_state"] == "OFF_HOURS"
        assert result["requirements"]["context_budget"] == "light"

    def test_off_hours_preserves_expert_classification(self, base_state, base_dynamics):
        # Same observation under WORK and OFF_HOURS should yield same expert
        obs_work = _make_obs(base_state, base_dynamics, ScheduleKind.WORK)
        obs_off = _make_obs(base_state, base_dynamics, ScheduleKind.OFF_HOURS)
        r_work = compute_routing(obs_work, base_state)
        r_off = compute_routing(obs_off, base_state)
        assert r_off["expert"] == r_work["expert"]


class TestFamily:
    def test_family_forces_restorer(self, base_state, base_dynamics):
        obs = _make_obs(base_state, base_dynamics, ScheduleKind.FAMILY)
        result = compute_routing(obs, base_state)
        assert result["expert"] == "restorer"
        assert result["requirements"]["requires_coding"] is False
        assert result["requirements"]["context_budget"] == "light"
        assert result["requirements"]["supported_tasks"] == ["coaching"]

    def test_family_consent_ignored(self, base_state, base_dynamics):
        """FAMILY mirrors RED — consent does not unlock normal routing."""
        obs = _make_obs(base_state, base_dynamics, ScheduleKind.FAMILY)
        with_consent = compute_routing(obs, base_state, has_valid_consent=True)
        without_consent = compute_routing(obs, base_state, has_valid_consent=False)
        assert with_consent["expert"] == "restorer"
        assert without_consent["expert"] == "restorer"


class TestOverrideReason:
    def test_override_reason_flows_through(self, base_state, base_dynamics):
        obs = _make_obs(
            base_state, base_dynamics,
            ScheduleKind.FAMILY, override_reason="vacation",
        )
        result = compute_routing(obs, base_state)
        assert result["schedule_override_reason"] == "vacation"
        assert result["expert"] == "restorer"

    def test_empty_override_reason_default(self, base_state, base_dynamics):
        obs = _make_obs(base_state, base_dynamics, ScheduleKind.WORK)
        result = compute_routing(obs, base_state)
        assert result["schedule_override_reason"] == ""


class TestInteractionWithBurnout:
    def test_red_and_family_both_yield_restorer(self, base_dynamics):
        red_state = StateBlock(burnout=Burnout.RED)
        obs = _make_obs(red_state, base_dynamics, ScheduleKind.FAMILY)
        result = compute_routing(obs, red_state)
        assert result["expert"] == "restorer"
        assert result["schedule_state"] == "FAMILY"

    def test_orange_no_consent_and_off_hours_still_restorer(self, base_dynamics):
        """ORANGE without consent already forces restorer — OFF_HOURS keeps light context."""
        orange_state = StateBlock(burnout=Burnout.ORANGE)
        obs = _make_obs(orange_state, base_dynamics, ScheduleKind.OFF_HOURS)
        result = compute_routing(obs, orange_state, has_valid_consent=False)
        assert result["expert"] == "restorer"
        assert result["requirements"]["context_budget"] == "light"
