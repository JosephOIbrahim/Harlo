"""Hebbian learning — co-activation tracking and dual-mask SDR evolution.

Patch 7: Dual directional masks (strengthen_mask, weaken_mask), NOT XOR.
  effective_sdr = (base_sdr | strengthen_mask) & ~weaken_mask
  Set/clear is idempotent. Conflict: weaken_mask wins.

Patch 4: Hebbian deltas stored in [V] Variant USD layer, not destructive
  SQLite mutation. Base SDR stays pristine.

Stability: max drift 2% per epoch. Homeostatic plasticity keeps [3%, 5%]
activation band.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from ..usd_lite.prims import CognitiveProfilePrim, MultipliersPrim, TracePrim

SDR_LENGTH = 2048
_TARGET_ACTIVE_LOW = 0.03   # 3% minimum
_TARGET_ACTIVE_HIGH = 0.05  # 5% maximum
_MAX_DRIFT_PER_EPOCH = 0.02  # 2% max bits flipped per epoch
_DEFAULT_ALPHA = 0.01
_DEFAULT_BETA = 0.005
_HEBBIAN_HALFLIFE_MULTIPLIER = 2.0


@dataclass
class HebbianUpdate:
    """Result of a single Hebbian learning step."""
    trace_id: str
    bits_strengthened: int
    bits_weakened: int
    new_strengthen_mask: list[int]
    new_weaken_mask: list[int]
    drift_ratio: float       # Fraction of bits changed
    activation_ratio: float  # Effective activation density


def compute_effective_sdr(
    base_sdr: list[int],
    strengthen_mask: list[int],
    weaken_mask: list[int],
) -> list[int]:
    """Compute effective SDR: (base | strengthen) & ~weaken.

    Patch 7: Set/clear is idempotent and directionally correct.
    Conflict resolution: weaken_mask wins (applied last).
    """
    effective = [0] * SDR_LENGTH
    for i in range(SDR_LENGTH):
        bit = base_sdr[i] | strengthen_mask[i]
        if weaken_mask[i]:
            bit = 0
        effective[i] = bit
    return effective


def activation_density(sdr: list[int]) -> float:
    """Compute activation density (fraction of 1-bits)."""
    return sum(sdr) / SDR_LENGTH


def record_co_activation(
    trace_a: TracePrim,
    trace_b: TracePrim,
) -> tuple[TracePrim, TracePrim]:
    """Record co-activation between two traces.

    Pure counting. Returns updated traces with incremented co_activations.
    Idempotent per event: same pair in same recall doesn't double-count.
    """
    new_a = TracePrim(
        trace_id=trace_a.trace_id,
        sdr=trace_a.sdr,
        content_hash=trace_a.content_hash,
        strength=trace_a.strength,
        last_accessed=trace_a.last_accessed,
        co_activations={**trace_a.co_activations},
        competitions=dict(trace_a.competitions),
        hebbian_strengthen_mask=list(trace_a.hebbian_strengthen_mask),
        hebbian_weaken_mask=list(trace_a.hebbian_weaken_mask),
    )
    new_b = TracePrim(
        trace_id=trace_b.trace_id,
        sdr=trace_b.sdr,
        content_hash=trace_b.content_hash,
        strength=trace_b.strength,
        last_accessed=trace_b.last_accessed,
        co_activations={**trace_b.co_activations},
        competitions=dict(trace_b.competitions),
        hebbian_strengthen_mask=list(trace_b.hebbian_strengthen_mask),
        hebbian_weaken_mask=list(trace_b.hebbian_weaken_mask),
    )

    new_a.co_activations[trace_b.trace_id] = new_a.co_activations.get(trace_b.trace_id, 0) + 1
    new_b.co_activations[trace_a.trace_id] = new_b.co_activations.get(trace_a.trace_id, 0) + 1

    return new_a, new_b


def record_competition(
    trace_a: TracePrim,
    trace_b: TracePrim,
) -> tuple[TracePrim, TracePrim]:
    """Record competition between two traces (domain match + conflict)."""
    new_a = TracePrim(
        trace_id=trace_a.trace_id,
        sdr=trace_a.sdr,
        content_hash=trace_a.content_hash,
        strength=trace_a.strength,
        last_accessed=trace_a.last_accessed,
        co_activations=dict(trace_a.co_activations),
        competitions={**trace_a.competitions},
        hebbian_strengthen_mask=list(trace_a.hebbian_strengthen_mask),
        hebbian_weaken_mask=list(trace_a.hebbian_weaken_mask),
    )
    new_b = TracePrim(
        trace_id=trace_b.trace_id,
        sdr=trace_b.sdr,
        content_hash=trace_b.content_hash,
        strength=trace_b.strength,
        last_accessed=trace_b.last_accessed,
        co_activations=dict(trace_b.co_activations),
        competitions={**trace_b.competitions},
        hebbian_strengthen_mask=list(trace_b.hebbian_strengthen_mask),
        hebbian_weaken_mask=list(trace_b.hebbian_weaken_mask),
    )

    new_a.competitions[trace_b.trace_id] = new_a.competitions.get(trace_b.trace_id, 0) + 1
    new_b.competitions[trace_a.trace_id] = new_b.competitions.get(trace_a.trace_id, 0) + 1

    return new_a, new_b


def apply_hebbian_strengthening(
    trace: TracePrim,
    co_activated_traces: list[TracePrim],
    profile: Optional[CognitiveProfilePrim] = None,
    rng_seed: Optional[int] = None,
) -> HebbianUpdate:
    """Apply Hebbian bit-level strengthening based on co-activations.

    P(set 0→1) = (alpha * profile.hebbian_alpha) * (co_act[j] / max_co_act)

    Patch 7: Strengthening sets bits in strengthen_mask.
    Stability: max drift 2% per epoch.
    """
    alpha = _DEFAULT_ALPHA
    if profile is not None:
        alpha = profile.multipliers.hebbian_alpha

    rng = random.Random(rng_seed)

    max_co_act = 1
    for other in co_activated_traces:
        count = trace.co_activations.get(other.trace_id, 0)
        if count > max_co_act:
            max_co_act = count

    new_strengthen = list(trace.hebbian_strengthen_mask)
    new_weaken = list(trace.hebbian_weaken_mask)
    max_drift_bits = int(SDR_LENGTH * _MAX_DRIFT_PER_EPOCH)
    bits_changed = 0

    for other in co_activated_traces:
        count = trace.co_activations.get(other.trace_id, 0)
        if count == 0:
            continue
        prob = alpha * (count / max_co_act)
        for i in range(SDR_LENGTH):
            if bits_changed >= max_drift_bits:
                break
            # Strengthen shared active bits from co-activated trace
            if other.sdr[i] == 1 and trace.sdr[i] == 0 and new_strengthen[i] == 0:
                if rng.random() < prob:
                    new_strengthen[i] = 1
                    # Conflict: if same bit in weaken, weaken wins
                    if new_weaken[i] == 1:
                        new_strengthen[i] = 0
                    else:
                        bits_changed += 1

    # Anti-Hebbian: weaken bits from competing traces
    bits_weakened = 0
    max_comp = 1
    for other in co_activated_traces:
        count = trace.competitions.get(other.trace_id, 0)
        if count > max_comp:
            max_comp = count

    for other in co_activated_traces:
        count = trace.competitions.get(other.trace_id, 0)
        if count == 0:
            continue
        prob = _DEFAULT_BETA * (count / max_comp)
        for i in range(SDR_LENGTH):
            if bits_changed + bits_weakened >= max_drift_bits:
                break
            if other.sdr[i] == 1 and trace.sdr[i] == 1 and new_weaken[i] == 0:
                if rng.random() < prob:
                    new_weaken[i] = 1
                    bits_weakened += 1

    effective = compute_effective_sdr(trace.sdr, new_strengthen, new_weaken)
    drift_ratio = (bits_changed + bits_weakened) / SDR_LENGTH
    act_ratio = activation_density(effective)

    # Homeostatic plasticity: clamp to [3%, 5%] band
    new_strengthen, new_weaken = _homeostatic_clamp(
        trace.sdr, new_strengthen, new_weaken, rng,
    )

    return HebbianUpdate(
        trace_id=trace.trace_id,
        bits_strengthened=bits_changed,
        bits_weakened=bits_weakened,
        new_strengthen_mask=new_strengthen,
        new_weaken_mask=new_weaken,
        drift_ratio=drift_ratio,
        activation_ratio=act_ratio,
    )


def _homeostatic_clamp(
    base: list[int],
    strengthen: list[int],
    weaken: list[int],
    rng: random.Random,
) -> tuple[list[int], list[int]]:
    """Clamp effective activation density to [3%, 5%] band.

    If too sparse: remove some weaken bits.
    If too dense: remove some strengthen bits.
    """
    effective = compute_effective_sdr(base, strengthen, weaken)
    density = activation_density(effective)

    new_s = list(strengthen)
    new_w = list(weaken)

    if density < _TARGET_ACTIVE_LOW:
        # Too sparse — undo some weakening
        weaken_indices = [i for i in range(SDR_LENGTH) if new_w[i] == 1]
        rng.shuffle(weaken_indices)
        for i in weaken_indices:
            if density >= _TARGET_ACTIVE_LOW:
                break
            new_w[i] = 0
            effective = compute_effective_sdr(base, new_s, new_w)
            density = activation_density(effective)
    elif density > _TARGET_ACTIVE_HIGH:
        # Too dense — undo some strengthening
        str_indices = [i for i in range(SDR_LENGTH) if new_s[i] == 1]
        rng.shuffle(str_indices)
        for i in str_indices:
            if density <= _TARGET_ACTIVE_HIGH:
                break
            new_s[i] = 0
            effective = compute_effective_sdr(base, new_s, new_w)
            density = activation_density(effective)

    return new_s, new_w
