"""Trajectory Generator — Forward-chaining causal simulator.

Commandment 11: Profile-Driven Markov Biasing, NOT uniform random sampling.
Deep Work sessions forcibly skew coherence/velocity to 95%+ to guarantee burst reachable.

Distribution targets (±5%):
  normal=40%, deep_work=15%, struggling=15%, recovery=10%,
  injection=10%, crisis=5%, mobile=5%

Output: JSONL trajectories + reports.
"""

from __future__ import annotations

import json
import math
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .mock_cogexec import evaluate_dag
from .mock_usd_stage import MockUsdStage
from .schemas import (
    ActionBlock,
    ActionType,
    AllostasisBlock,
    AllostasisTrend,
    BurstPhase,
    Burnout,
    CognitiveObservation,
    ContextLevel,
    DelegateBlock,
    DynamicsBlock,
    Energy,
    InjectionBlock,
    InjectionPhase,
    InjectionProfile,
    Momentum,
    SleepQuality,
    StateBlock,
)
from .validator import validate_trajectory


# -------------------------------------------------------------------
# Session profile definitions (Markov biasing)
# -------------------------------------------------------------------

@dataclass
class SessionProfile:
    """Defines biases for a session type."""
    name: str
    min_exchanges: int
    max_exchanges: int
    coherence_range: tuple[float, float]
    velocity_range: tuple[float, float]
    frustration_range: tuple[float, float]
    injection_profile: InjectionProfile = InjectionProfile.NONE
    sleep_quality: SleepQuality = SleepQuality.GOOD
    exercise_recency: int = 1
    force_red: bool = False
    target_pct: float = 0.0


PROFILES: dict[str, SessionProfile] = {
    "normal": SessionProfile(
        name="normal",
        min_exchanges=15, max_exchanges=40,
        coherence_range=(0.5, 0.85),
        velocity_range=(0.3, 0.7),
        frustration_range=(0.0, 0.3),
        target_pct=0.40,
    ),
    "deep_work": SessionProfile(
        name="deep_work",
        min_exchanges=30, max_exchanges=80,
        coherence_range=(0.90, 0.99),  # Commandment 11: skew to 95%+
        velocity_range=(0.85, 0.99),   # Commandment 11: skew to 95%+
        frustration_range=(0.0, 0.1),
        sleep_quality=SleepQuality.GOOD,
        exercise_recency=0,
        target_pct=0.15,
    ),
    "struggling": SessionProfile(
        name="struggling",
        min_exchanges=10, max_exchanges=30,
        coherence_range=(0.2, 0.5),
        velocity_range=(0.1, 0.4),
        frustration_range=(0.4, 0.8),
        sleep_quality=SleepQuality.POOR,
        exercise_recency=3,
        target_pct=0.15,
    ),
    "recovery": SessionProfile(
        name="recovery",
        min_exchanges=5, max_exchanges=15,
        coherence_range=(0.3, 0.6),
        velocity_range=(0.2, 0.4),
        frustration_range=(0.0, 0.2),
        exercise_recency=0,
        target_pct=0.10,
    ),
    "injection": SessionProfile(
        name="injection",
        min_exchanges=20, max_exchanges=60,
        coherence_range=(0.4, 0.9),
        velocity_range=(0.3, 0.8),
        frustration_range=(0.0, 0.3),
        injection_profile=InjectionProfile.MICRODOSE,
        target_pct=0.10,
    ),
    "crisis": SessionProfile(
        name="crisis",
        min_exchanges=5, max_exchanges=15,
        coherence_range=(0.1, 0.3),
        velocity_range=(0.1, 0.3),
        frustration_range=(0.7, 1.0),
        force_red=True,
        sleep_quality=SleepQuality.POOR,
        exercise_recency=5,
        target_pct=0.05,
    ),
    "mobile": SessionProfile(
        name="mobile",
        min_exchanges=3, max_exchanges=10,
        coherence_range=(0.4, 0.7),
        velocity_range=(0.2, 0.5),
        frustration_range=(0.0, 0.2),
        target_pct=0.05,
    ),
}


def _pick_profile(rng: random.Random) -> SessionProfile:
    """Weighted random selection of session profile."""
    names = list(PROFILES.keys())
    weights = [PROFILES[n].target_pct for n in names]
    chosen = rng.choices(names, weights=weights, k=1)[0]
    return PROFILES[chosen]


def _pick_injection_profile(rng: random.Random) -> InjectionProfile:
    """Pick a random injection profile (not NONE)."""
    profiles = [InjectionProfile.MICRODOSE, InjectionProfile.PERCEPTUAL,
                InjectionProfile.CLASSICAL, InjectionProfile.MDMA]
    return rng.choice(profiles)


def _injection_alpha_curve(phase: InjectionPhase, exchange_in_phase: int,
                           phase_duration: int) -> float:
    """Compute alpha based on pharmacokinetic phase."""
    t = exchange_in_phase / max(phase_duration, 1)
    if phase == InjectionPhase.ONSET:
        return min(t * 1.2, 1.0)
    elif phase == InjectionPhase.PLATEAU:
        return 0.8 + 0.2 * math.sin(math.pi * t)
    elif phase == InjectionPhase.OFFSET:
        return max(1.0 - t * 1.2, 0.0)
    return 0.0


def _pick_action_type(rng: random.Random, profile: SessionProfile,
                      exchange_idx: int, num_exchanges: int) -> ActionType:
    """Pick action type based on profile and position."""
    if exchange_idx == 0:
        return ActionType.SESSION_START
    if exchange_idx == num_exchanges - 1:
        return ActionType.SESSION_END

    if profile.name == "crisis":
        return rng.choices(
            [ActionType.QUERY, ActionType.OVERRIDE, ActionType.PERMISSION_GRANT],
            weights=[0.5, 0.3, 0.2], k=1
        )[0]

    if profile.name == "deep_work":
        return rng.choices(
            [ActionType.QUERY, ActionType.DIRECTIVE, ActionType.BURST_CONTINUE],
            weights=[0.3, 0.3, 0.4], k=1
        )[0]

    return rng.choices(
        [ActionType.QUERY, ActionType.DIRECTIVE, ActionType.TANGENT,
         ActionType.OVERRIDE, ActionType.SWITCH],
        weights=[0.4, 0.25, 0.15, 0.1, 0.1], k=1
    )[0]


def generate_session(
    rng: random.Random,
    profile: Optional[SessionProfile] = None,
    session_id: Optional[str] = None,
) -> list[CognitiveObservation]:
    """Generate a single session trajectory using forward-chaining simulation.

    Commandment 2: Bridge/Generator maintains and authors accumulators per exchange.
    Commandment 11: Profile-Driven Markov Biasing.
    """
    if profile is None:
        profile = _pick_profile(rng)
    if session_id is None:
        session_id = str(uuid.uuid4())[:8]

    num_exchanges = rng.randint(profile.min_exchanges, profile.max_exchanges)
    stage = MockUsdStage()
    observations: list[CognitiveObservation] = []

    # Injection state tracking
    inj_profile = InjectionProfile.NONE
    inj_phase = InjectionPhase.BASELINE
    inj_phase_start = 0
    inj_phase_duration = 0

    if profile.injection_profile != InjectionProfile.NONE:
        inj_profile = _pick_injection_profile(rng)
        inj_phase = InjectionPhase.ONSET
        inj_phase_start = 0
        inj_phase_duration = max(num_exchanges // 4, 3)

    # Accumulator state (authored by generator, NOT tracked internally)
    tasks_completed = 0
    exchanges_without_break = 0
    adrenaline_debt = 0
    tangent_budget = 4.0
    prev_burst = BurstPhase.NONE

    # RED event timing for crisis sessions
    red_exchange = -1
    if profile.force_red:
        red_exchange = rng.randint(num_exchanges // 3, num_exchanges - 2)

    for i in range(num_exchanges):
        # Sample dynamics from profile ranges
        coherence = rng.uniform(*profile.coherence_range)
        velocity = rng.uniform(*profile.velocity_range)
        frustration = rng.uniform(*profile.frustration_range)

        # Task completion (probabilistic)
        if rng.random() < velocity * 0.3:
            tasks_completed += 1

        # Break logic
        exchanges_without_break += 1
        if rng.random() < 0.05 and i > 5:
            exchanges_without_break = 0

        # Tangent budget deduction
        action_type = _pick_action_type(rng, profile, i, num_exchanges)
        if action_type == ActionType.TANGENT:
            tangent_budget = max(tangent_budget - 1.0, 0.0)

        # Adrenaline debt tracking (Commandment 8)
        if prev_burst >= BurstPhase.DETECTED:
            adrenaline_debt += 1
        if prev_burst == BurstPhase.NONE and adrenaline_debt > 0:
            # Debt applied by compute_energy, reset after application
            pass

        # Injection phase progression
        alpha = 0.0
        if inj_profile != InjectionProfile.NONE:
            exchange_in_phase = i - inj_phase_start
            if exchange_in_phase >= inj_phase_duration and inj_phase < InjectionPhase.OFFSET:
                inj_phase = InjectionPhase(int(inj_phase) + 1)
                inj_phase_start = i
                inj_phase_duration = max(num_exchanges // 4, 3)
                exchange_in_phase = 0
            if inj_phase == InjectionPhase.BASELINE and i > inj_phase_duration * 3:
                inj_profile = InjectionProfile.NONE
            alpha = _injection_alpha_curve(inj_phase, exchange_in_phase, inj_phase_duration)

        # Build observation
        obs = CognitiveObservation(
            session_id=session_id,
            observation_index=i,
            exchange_index=i,
            wall_clock_delta=rng.uniform(5.0, 120.0),
            state=StateBlock(
                exercise_recency_days=profile.exercise_recency,
                sleep_quality=profile.sleep_quality,
            ),
            action=ActionBlock(action_type=action_type),
            dynamics=DynamicsBlock(
                exchange_velocity=velocity,
                topic_coherence=coherence,
                session_exchange_count=i,
                tangent_budget_remaining=tangent_budget,
                exchanges_without_break=exchanges_without_break,
                adrenaline_debt=adrenaline_debt if prev_burst == BurstPhase.NONE else 0,
                tasks_completed=tasks_completed,
                frustration_signal=frustration,
            ),
            injection=InjectionBlock(
                profile=inj_profile,
                alpha=round(alpha, 4),
                phase=inj_phase if inj_profile != InjectionProfile.NONE else InjectionPhase.BASELINE,
            ),
            allostasis=AllostasisBlock(
                sessions_24h=rng.randint(1, 5),
                override_ratio_7d=rng.uniform(0.0, 0.3),
            ),
        )

        # Evaluate through DAG
        exogenous_red = (i == red_exchange)
        resolved = evaluate_dag(
            stage, obs, i,
            exogenous_red=exogenous_red,
            token_ratio=rng.uniform(2.0, 6.0),
        )

        # Track burst for adrenaline debt
        prev_burst = resolved.dynamics.burst_phase
        if resolved.dynamics.burst_phase == BurstPhase.NONE and adrenaline_debt > 0:
            adrenaline_debt = 0

        observations.append(resolved)

    return observations


@dataclass
class GenerationReport:
    """Report on trajectory generation results."""
    total_sessions: int = 0
    total_exchanges: int = 0
    valid_sessions: int = 0
    invalid_sessions: int = 0
    violations: list[str] = field(default_factory=list)
    profile_distribution: dict[str, int] = field(default_factory=dict)
    edge_cases: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "total_sessions": self.total_sessions,
            "total_exchanges": self.total_exchanges,
            "valid_sessions": self.valid_sessions,
            "invalid_sessions": self.invalid_sessions,
            "violation_count": len(self.violations),
            "violations_sample": self.violations[:20],
            "profile_distribution": self.profile_distribution,
            "edge_cases": self.edge_cases,
        }


def _detect_edge_cases(observations: list[CognitiveObservation]) -> dict[str, bool]:
    """Detect which edge cases are present in a trajectory."""
    cases: dict[str, bool] = {
        "red_during_burst": False,
        "injection_during_depleted": False,
        "adrenaline_debt_on_exit": False,
        "rising_allostatic": False,
        "permission_override": False,
        "peak_momentum": False,
        "crisis_recovery": False,
    }

    for i, obs in enumerate(observations):
        if (obs.state.burnout == Burnout.RED
                and obs.dynamics.burst_phase >= BurstPhase.DETECTED):
            cases["red_during_burst"] = True

        if (obs.injection.profile != InjectionProfile.NONE
                and obs.state.energy == Energy.DEPLETED):
            cases["injection_during_depleted"] = True

        if obs.dynamics.adrenaline_debt > 0 and obs.dynamics.burst_phase == BurstPhase.NONE:
            cases["adrenaline_debt_on_exit"] = True

        if obs.allostasis.trend in (AllostasisTrend.RISING, AllostasisTrend.SPIKE):
            cases["rising_allostatic"] = True

        if obs.action.action_type == ActionType.OVERRIDE:
            cases["permission_override"] = True

        if obs.state.momentum == Momentum.PEAK:
            cases["peak_momentum"] = True

        if (i > 0 and observations[i-1].state.burnout == Burnout.RED
                and obs.state.burnout < Burnout.RED):
            cases["crisis_recovery"] = True

    return cases


def generate_trajectories(
    count: int = 100,
    seed: int = 42,
    validate: bool = True,
    output_path: Optional[str] = None,
) -> GenerationReport:
    """Generate multiple session trajectories.

    Args:
        count: Number of sessions to generate.
        seed: Random seed for reproducibility.
        validate: Whether to run invariant validation.
        output_path: Optional JSONL output file path.
    """
    rng = random.Random(seed)
    report = GenerationReport()
    all_trajectories: list[list[dict]] = []

    for session_idx in range(count):
        profile = _pick_profile(rng)
        session_id = f"s{session_idx:05d}"

        trajectory = generate_session(rng, profile=profile, session_id=session_id)
        report.total_sessions += 1
        report.total_exchanges += len(trajectory)

        # Track profile distribution
        report.profile_distribution[profile.name] = (
            report.profile_distribution.get(profile.name, 0) + 1
        )

        # Detect edge cases
        edge_cases = _detect_edge_cases(trajectory)
        for case_name, present in edge_cases.items():
            if present:
                report.edge_cases[case_name] = report.edge_cases.get(case_name, 0) + 1

        # Validate
        if validate:
            violations = validate_trajectory(trajectory)
            if violations:
                report.invalid_sessions += 1
                report.violations.extend(violations[:5])
            else:
                report.valid_sessions += 1
        else:
            report.valid_sessions += 1

        # Serialize
        all_trajectories.append([obs.model_dump() for obs in trajectory])

    # Write JSONL
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            for traj in all_trajectories:
                f.write(json.dumps(traj) + "\n")

    return report


def main():
    """CLI entry point for trajectory generation."""
    import argparse
    parser = argparse.ArgumentParser(description="Generate cognitive state trajectories")
    parser.add_argument("--count", type=int, default=100, help="Number of sessions")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--validate", action="store_true", help="Run validation")
    parser.add_argument("--output", type=str, default=None, help="JSONL output path")
    args = parser.parse_args()

    report = generate_trajectories(
        count=args.count,
        seed=args.seed,
        validate=args.validate,
        output_path=args.output,
    )

    print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
