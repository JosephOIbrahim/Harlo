"""MockCogExec — networkx DAG for topologically sorted cognitive state evaluation.

Commandment 2: All computations are pure functions.
Commandment 4: State machines read t-1 from authored history. No self-query cycles.

The DAG defines computation dependencies:
  burst → energy → momentum → burnout → allostasis
  injection_gain (independent)
  context_budget (independent)
"""

from __future__ import annotations

from typing import Any, Callable

import networkx as nx

from .mock_usd_stage import MockUsdStage
from .schemas import (
    AllostasisBlock,
    BurstPhase,
    CognitiveObservation,
    ContextLevel,
    DynamicsBlock,
    Momentum,
    Burnout,
    Energy,
    StateBlock,
)
from .computations.compute_burst import compute_burst
from .computations.compute_energy import compute_energy
from .computations.compute_momentum import compute_momentum
from .computations.compute_burnout import compute_burnout
from .computations.compute_injection_gain import compute_injection_gain, compute_anchor_gain
from .computations.compute_context_budget import compute_context_budget
from .computations.compute_allostasis import compute_allostasis


def build_dag() -> nx.DiGraph:
    """Build the cognitive computation DAG.

    Edges encode dependencies (A → B means A must compute before B).
    """
    g = nx.DiGraph()

    # Nodes: computation names
    g.add_node("burst")
    g.add_node("energy")
    g.add_node("momentum")
    g.add_node("burnout")
    g.add_node("allostasis")
    g.add_node("injection_gain")
    g.add_node("context_budget")

    # Dependencies
    g.add_edge("burst", "energy")        # energy needs burst (adrenaline masking)
    g.add_edge("energy", "momentum")     # momentum needs energy (depleted affects it)
    g.add_edge("momentum", "burnout")    # burnout needs momentum (peak detection)
    g.add_edge("burnout", "allostasis")  # allostasis needs burnout level
    # injection_gain and context_budget are independent

    return g


def evaluate_dag(
    stage: MockUsdStage,
    authored: CognitiveObservation,
    exchange_index: int,
    prim_path: str = "/state",
    exogenous_red: bool = False,
    token_ratio: float = 1.0,
    domain: str = "",
) -> CognitiveObservation:
    """Evaluate the full cognitive DAG for one exchange.

    Reads previous state from stage (Commandment 4: read t-1).
    Computes all state transitions in topological order.
    Returns the fully resolved CognitiveObservation for this exchange.
    """
    dag = build_dag()
    order = list(nx.topological_sort(dag))

    # Read previous state (Commandment 5: baseline at index 0)
    prev: CognitiveObservation = stage.read_previous(prim_path, exchange_index)
    prev_state = prev.state
    prev_dynamics = prev.dynamics
    prev_allostasis = prev.allostasis

    # Mutable result accumulator
    new_state = authored.state.model_copy()
    new_dynamics = authored.dynamics.model_copy()

    results: dict[str, Any] = {}

    for node in order:
        if node == "burst":
            new_burst = compute_burst(
                authored,
                prev_dynamics,
                burst_detect_velocity=stage.get_threshold("burst_detect_velocity"),
                burst_detect_coherence=stage.get_threshold("burst_detect_coherence"),
                burst_winding_exchange=stage.get_threshold("burst_winding_exchange"),
                burst_exit_exchange=stage.get_threshold("burst_exit_exchange"),
            )
            new_dynamics.burst_phase = new_burst
            results["burst"] = new_burst

        elif node == "energy":
            # Update authored dynamics with computed burst before energy calc
            authored_with_burst = authored.model_copy(deep=True)
            authored_with_burst.dynamics.burst_phase = results.get("burst", authored.dynamics.burst_phase)
            new_energy = compute_energy(
                authored_with_burst,
                prev_state,
                energy_decrement_interval=stage.get_threshold("energy_decrement_interval"),
            )
            new_state.energy = new_energy
            results["energy"] = new_energy

        elif node == "momentum":
            authored_for_momentum = authored.model_copy(deep=True)
            authored_for_momentum.dynamics.burst_phase = results.get("burst", authored.dynamics.burst_phase)
            new_momentum = compute_momentum(
                authored_for_momentum,
                prev_state,
                building_task_threshold=stage.get_threshold("building_task_threshold"),
                rolling_coherence_threshold=stage.get_threshold("rolling_coherence_threshold"),
                rolling_velocity_threshold=stage.get_threshold("rolling_velocity_threshold"),
                peak_exchange_threshold=stage.get_threshold("peak_exchange_threshold"),
            )
            new_state.momentum = new_momentum
            results["momentum"] = new_momentum

        elif node == "burnout":
            new_burnout = compute_burnout(
                authored,
                prev_state,
                exogenous_red=exogenous_red,
                frustration_burnout_threshold=stage.get_threshold("frustration_burnout_threshold"),
                burnout_exchange_yellow=stage.get_threshold("burnout_exchange_yellow"),
                burnout_exchange_orange=stage.get_threshold("burnout_exchange_orange"),
            )
            new_state.burnout = new_burnout
            results["burnout"] = new_burnout

        elif node == "allostasis":
            # Build authored with resolved burnout for allostasis
            authored_for_allo = authored.model_copy(deep=True)
            authored_for_allo.state.burnout = results.get("burnout", authored.state.burnout)
            new_allo = compute_allostasis(authored_for_allo, prev_allostasis)
            results["allostasis"] = new_allo

        elif node == "injection_gain":
            gain = compute_injection_gain(authored, domain)
            results["injection_gain"] = gain

        elif node == "context_budget":
            new_context = compute_context_budget(
                authored,
                prev_state,
                token_ratio=token_ratio,
                promote_threshold=stage.get_threshold("context_promote_threshold"),
                demote_threshold=stage.get_threshold("context_demote_threshold"),
            )
            new_state.context = new_context
            results["context_budget"] = new_context

    # Assemble final observation
    resolved = authored.model_copy(deep=True)
    resolved.state = new_state
    resolved.dynamics = new_dynamics
    if "allostasis" in results:
        resolved.allostasis = results["allostasis"]

    # Author to stage
    stage.author(prim_path, exchange_index, resolved)

    return resolved
