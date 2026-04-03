#!/usr/bin/env python3
"""Hebbian co-activation seeding for demo purposes.

Loads 16 traces from SQLite (READ ONLY), records co-activations between
semantically related groups, runs 3 epochs of Hebbian strengthening,
and persists results to data/hebbian_seeded.usda + data/hebbian_seed_report.json.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "python"))

from harlo.hebbian.learning import (
    SDR_LENGTH,
    HebbianUpdate,
    activation_density,
    apply_hebbian_strengthening,
    compute_effective_sdr,
    record_co_activation,
)
from harlo.usd_lite.hex_sdr import sdr_to_hex
from harlo.usd_lite.prims import AssociationPrim, TracePrim
from harlo.usd_lite.serializer import serialize
from harlo.usd_lite.stage import BrainStage

DB_PATH = _PROJECT_ROOT / "data" / "twin.db"
OUTPUT_USDA = _PROJECT_ROOT / "data" / "hebbian_seeded.usda"
OUTPUT_REPORT = _PROJECT_ROOT / "data" / "hebbian_seed_report.json"

# ---------------------------------------------------------------------------
# Co-activation group definitions
# ---------------------------------------------------------------------------
GROUPS: dict[str, tuple[list[str], int]] = {
    "A": (["t1", "t2", "b7579090c5e54a59"], 3),
    "B": (["2e10f353f39f495b", "db4ae533b5be471f", "d2eb1be2a33640a7"], 3),
    "C": (["5d8a7e55864b4790", "81b3464ba8c941f0"], 3),
    "D": (["671ec3412e27484c", "26ab7b0812da44b4"], 3),
    "E": (["t3", "t4", "f22d233961a44636", "test-v7-001"], 2),
    "F": (["b0fbfe68328848dd", "t4"], 2),
}


def bytes_to_sdr(data: bytes) -> list[int]:
    """Convert 256 bytes (2048 bits) to list[int] of 0/1."""
    sdr: list[int] = []
    for byte_val in data:
        for bit in range(7, -1, -1):
            sdr.append((byte_val >> bit) & 1)
    return sdr


def load_traces(db_path: Path) -> dict[str, TracePrim]:
    """Load first 16 traces from SQLite (READ ONLY)."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cur = conn.execute(
            "SELECT id, sdr_blob, initial_strength, last_accessed FROM traces LIMIT 16"
        )
        traces: dict[str, TracePrim] = {}
        for row in cur.fetchall():
            trace_id = row[0]
            sdr_blob = row[1]
            strength = row[2]
            last_accessed_ts = row[3]

            sdr = bytes_to_sdr(sdr_blob)
            content_hash = hashlib.sha256(sdr_blob).hexdigest()[:16]
            last_accessed = datetime.fromtimestamp(last_accessed_ts, tz=timezone.utc)

            traces[trace_id] = TracePrim(
                trace_id=trace_id,
                sdr=sdr,
                content_hash=content_hash,
                strength=strength,
                last_accessed=last_accessed,
            )
        return traces
    finally:
        conn.close()


def record_group_co_activations(
    traces: dict[str, TracePrim],
    groups: dict[str, tuple[list[str], int]],
) -> dict[str, TracePrim]:
    """Record co-activations for all pairs within each group."""
    for group_name, (members, reps) in groups.items():
        # Filter to members that exist in traces
        available = [m for m in members if m in traces]
        for id_a, id_b in combinations(available, 2):
            for _ in range(reps):
                new_a, new_b = record_co_activation(traces[id_a], traces[id_b])
                traces[id_a] = new_a
                traces[id_b] = new_b
    return traces


def run_hebbian_epochs(
    traces: dict[str, TracePrim],
    epochs: int = 3,
) -> dict[str, TracePrim]:
    """Run Hebbian strengthening epochs over all traces with co-activations."""
    for epoch in range(epochs):
        for trace_id in list(traces.keys()):
            trace = traces[trace_id]
            if not trace.co_activations:
                continue

            # Gather co-activated traces
            co_activated = []
            for other_id in trace.co_activations:
                if other_id in traces:
                    co_activated.append(traces[other_id])

            if not co_activated:
                continue

            # Deterministic seed: hash((trace_id, epoch))
            rng_seed = hash((trace_id, epoch)) & 0xFFFFFFFF

            update: HebbianUpdate = apply_hebbian_strengthening(
                trace, co_activated, profile=None, rng_seed=rng_seed,
            )

            # Update masks in master dict; DO NOT modify trace.sdr
            traces[trace_id] = TracePrim(
                trace_id=trace.trace_id,
                sdr=trace.sdr,
                content_hash=trace.content_hash,
                strength=trace.strength,
                last_accessed=trace.last_accessed,
                co_activations=dict(trace.co_activations),
                competitions=dict(trace.competitions),
                hebbian_strengthen_mask=update.new_strengthen_mask,
                hebbian_weaken_mask=update.new_weaken_mask,
            )
    return traces


def persist_usda(traces: dict[str, TracePrim], output_path: Path) -> None:
    """Persist traces to .usda via BrainStage + serializer."""
    stage = BrainStage(
        association=AssociationPrim(traces=traces),
    )
    usda_text = serialize(stage)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(usda_text, encoding="utf-8")


def build_report(
    traces: dict[str, TracePrim],
    groups: dict[str, tuple[list[str], int]],
    epochs: int,
) -> dict:
    """Build the summary report dict."""
    per_trace: dict[str, dict] = {}
    traces_with_links = 0

    for trace_id, trace in traces.items():
        base_density = activation_density(trace.sdr)
        effective = compute_effective_sdr(
            trace.sdr,
            trace.hebbian_strengthen_mask,
            trace.hebbian_weaken_mask,
        )
        eff_density = activation_density(effective)
        strengthen_bits = sum(trace.hebbian_strengthen_mask)
        weaken_bits = sum(trace.hebbian_weaken_mask)
        link_count = len(trace.co_activations)

        if link_count > 0:
            traces_with_links += 1

        per_trace[trace_id] = {
            "co_activation_links": link_count,
            "strengthen_bits": strengthen_bits,
            "weaken_bits": weaken_bits,
            "effective_density": round(eff_density, 6),
            "base_density": round(base_density, 6),
        }

    # Build groups summary (only IDs, not reps)
    groups_summary = {k: v[0] for k, v in groups.items()}

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "traces_processed": len(traces),
        "traces_with_links": traces_with_links,
        "epochs": epochs,
        "groups": groups_summary,
        "per_trace": per_trace,
    }


def main() -> None:
    """Run the Hebbian seeding pipeline."""
    print(f"Loading traces from {DB_PATH} ...")
    traces = load_traces(DB_PATH)
    print(f"  Loaded {len(traces)} traces")

    print("Recording co-activations ...")
    traces = record_group_co_activations(traces, GROUPS)

    epochs = 3
    print(f"Running {epochs} Hebbian strengthening epochs ...")
    traces = run_hebbian_epochs(traces, epochs=epochs)

    print(f"Persisting to {OUTPUT_USDA} ...")
    persist_usda(traces, OUTPUT_USDA)

    print(f"Writing report to {OUTPUT_REPORT} ...")
    report = build_report(traces, GROUPS, epochs)
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8",
    )

    # Summary
    print("\n=== Hebbian Seed Summary ===")
    print(f"  Traces processed:  {report['traces_processed']}")
    print(f"  Traces with links: {report['traces_with_links']}")
    print(f"  Epochs:            {report['epochs']}")

    # Verification checks
    nonzero_strengthen = sum(
        1 for t in report["per_trace"].values() if t["strengthen_bits"] > 0
    )
    densities = [t["effective_density"] for t in report["per_trace"].values()]
    density_ok = all(0.03 <= d <= 0.05 for d in densities if d > 0)

    print(f"  Non-zero strengthen masks: {nonzero_strengthen}")
    print(f"  Density range: [{min(densities):.4f}, {max(densities):.4f}]")
    print(f"  All densities in [0.03, 0.05]: {density_ok}")

    if nonzero_strengthen < 10:
        print(f"  WARNING: Only {nonzero_strengthen} traces have non-zero strengthen masks (expected >= 10)")
    if not density_ok:
        print("  WARNING: Some effective densities outside [0.03, 0.05] band")

    print("\nDone.")


if __name__ == "__main__":
    main()
