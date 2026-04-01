"""Pydantic models for the Cognitive State Machine.

Commandment 1: No C++. Pure Python mock sprint.
Commandment 2: Pure functions with externally-authored accumulators.
Commandment 3: exchange_index is the ONLY temporal key.

Ordinal IntEnum for progressive states (GREEN=0..RED=3).
CognitiveObservation with full telemetry block.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, Field


# -------------------------------------------------------------------
# Ordinal IntEnum — progressive states (Commandment 10: ordinal encoding)
# -------------------------------------------------------------------

class Momentum(IntEnum):
    """Momentum phases. Ordinal: higher = more momentum."""
    CRASHED = 0
    COLD_START = 1
    BUILDING = 2
    ROLLING = 3
    PEAK = 4


class Burnout(IntEnum):
    """Burnout levels. Ordinal: higher = worse."""
    GREEN = 0
    YELLOW = 1
    ORANGE = 2
    RED = 3


class Energy(IntEnum):
    """Energy levels. Ordinal: higher = more energy."""
    DEPLETED = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Altitude(IntEnum):
    """Altitude levels for cognitive zoom."""
    GROUND = 0
    TEN_K = 1
    THIRTY_K = 2
    FIFTY_K = 3


class BurstPhase(IntEnum):
    """Hyperfocus burst phases."""
    NONE = 0
    DETECTED = 1
    PROTECTED = 2
    WINDING = 3
    EXIT_PREP = 4


class InjectionProfile(IntEnum):
    """Injection profiles."""
    NONE = 0
    MICRODOSE = 1
    PERCEPTUAL = 2
    CLASSICAL = 3
    MDMA = 4


class InjectionPhase(IntEnum):
    """Injection pharmacokinetic phase."""
    BASELINE = 0
    ONSET = 1
    PLATEAU = 2
    OFFSET = 3


class SleepQuality(IntEnum):
    """Sleep quality."""
    POOR = 0
    GOOD = 1


class ActionType(IntEnum):
    """Action types for trajectory observations."""
    SESSION_START = 0
    QUERY = 1
    DIRECTIVE = 2
    TANGENT = 3
    OVERRIDE = 4
    INJECTION = 5
    SWITCH = 6
    BURST_CONTINUE = 7
    PERMISSION_GRANT = 8
    SESSION_END = 9


class AllostasisTrend(IntEnum):
    """Allostatic load trend."""
    STABLE = 0
    RISING = 1
    FALLING = 2
    SPIKE = 3


class ContextLevel(IntEnum):
    """Context budget levels for LIVRPS composition."""
    PAYLOAD = 0
    REFERENCE = 1


# -------------------------------------------------------------------
# CognitiveObservation — the canonical observation schema
# -------------------------------------------------------------------

class StateBlock(BaseModel):
    """Current cognitive state at a given exchange."""
    momentum: Momentum = Momentum.COLD_START
    burnout: Burnout = Burnout.GREEN
    energy: Energy = Energy.MEDIUM
    altitude: Altitude = Altitude.GROUND
    exercise_recency_days: int = Field(default=0, ge=0)
    sleep_quality: SleepQuality = SleepQuality.GOOD
    context: ContextLevel = ContextLevel.REFERENCE


class ActionBlock(BaseModel):
    """Action taken at this exchange."""
    action_type: ActionType = ActionType.QUERY
    detail: str = ""


class DynamicsBlock(BaseModel):
    """Session dynamics at this exchange.

    Commandment 2: accumulators (exchanges_without_break, adrenaline_debt)
    are authored to the stage by the Bridge/Generator, NOT tracked internally.
    """
    exchange_velocity: float = Field(default=0.0, ge=0.0)
    topic_coherence: float = Field(default=1.0, ge=0.0, le=1.0)
    session_exchange_count: int = Field(default=0, ge=0)
    burst_phase: BurstPhase = BurstPhase.NONE
    tangent_budget_remaining: float = Field(default=4.0, ge=0.0)
    exchanges_without_break: int = Field(default=0, ge=0)
    adrenaline_debt: int = Field(default=0, ge=0)
    tasks_completed: int = Field(default=0, ge=0)
    frustration_signal: float = Field(default=0.0, ge=0.0, le=1.0)


class InjectionBlock(BaseModel):
    """Injection state at this exchange."""
    profile: InjectionProfile = InjectionProfile.NONE
    alpha: float = Field(default=0.0, ge=0.0, le=1.0)
    phase: InjectionPhase = InjectionPhase.BASELINE


class DelegateBlock(BaseModel):
    """Delegate (Claude mock) state."""
    active: bool = False
    task_type: str = ""


class AllostasisBlock(BaseModel):
    """Allostatic load tracking."""
    load: float = Field(default=0.0, ge=0.0, le=1.0)
    trend: AllostasisTrend = AllostasisTrend.STABLE
    sessions_24h: int = Field(default=1, ge=0)
    override_ratio_7d: float = Field(default=0.0, ge=0.0, le=1.0)


class CognitiveObservation(BaseModel):
    """Full cognitive observation at a single exchange.

    This is the canonical schema for trajectory generation and
    XGBoost prediction. Every field is typed and defaulted.
    """
    schema_name: str = "CognitiveObservation"
    version: str = "1.0"
    session_id: str = ""
    observation_index: int = Field(default=0, ge=0)
    exchange_index: int = Field(default=0, ge=0)
    wall_clock_delta: float = Field(default=0.0, ge=0.0)

    state: StateBlock = Field(default_factory=StateBlock)
    action: ActionBlock = Field(default_factory=ActionBlock)
    dynamics: DynamicsBlock = Field(default_factory=DynamicsBlock)
    injection: InjectionBlock = Field(default_factory=InjectionBlock)
    delegate: DelegateBlock = Field(default_factory=DelegateBlock)
    allostasis: AllostasisBlock = Field(default_factory=AllostasisBlock)


# -------------------------------------------------------------------
# Schema defaults for exchange_index == 0 (Commandment 5)
# -------------------------------------------------------------------

BASELINE_STATE = StateBlock(
    momentum=Momentum.COLD_START,
    burnout=Burnout.GREEN,
    energy=Energy.MEDIUM,
    altitude=Altitude.GROUND,
    exercise_recency_days=0,
    sleep_quality=SleepQuality.GOOD,
    context=ContextLevel.REFERENCE,
)

BASELINE_DYNAMICS = DynamicsBlock(
    exchange_velocity=0.0,
    topic_coherence=1.0,
    session_exchange_count=0,
    burst_phase=BurstPhase.NONE,
    tangent_budget_remaining=4.0,
    exchanges_without_break=0,
    adrenaline_debt=0,
    tasks_completed=0,
    frustration_signal=0.0,
)

BASELINE_INJECTION = InjectionBlock(
    profile=InjectionProfile.NONE,
    alpha=0.0,
    phase=InjectionPhase.BASELINE,
)

BASELINE_OBSERVATION = CognitiveObservation(
    state=BASELINE_STATE,
    dynamics=BASELINE_DYNAMICS,
    injection=BASELINE_INJECTION,
)
