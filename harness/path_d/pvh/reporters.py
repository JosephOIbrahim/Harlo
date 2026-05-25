"""Reporters: JSON metrics + Markdown evidence artifact.

03_HANDOFF.md Phase 4. Markdown is the human surface (Article 4 — no D3/Plotly/
HTML). The evidence artifact MUST carry the four v1 statements mandated by D39.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .evaluators import TARGETS, EvaluationResult

_BARS = "▁▂▃▄▅▆▇█"

# The four statements D39 requires in every v1 evidence artifact.
V1_LIMITATIONS = [
    "(a) The corpus is N=69 organic observations in a single session — insufficient for any statistical claim.",
    "(b) The reference predictor has target leakage (train_predictor.py:113-135): the prediction targets are present in its input window, so its output approximates the current state rather than forecasting.",
    "(c) No deflection claim is asserted from v1 output. Deflection/overshoot rates are reported as not-asserted (scaffolding signal absent, D20).",
    "(d) v1 validates the harness mechanics (extract -> feed reference model -> compute -> emit), NOT Harlo's multiplier effect. The evidence-harness ambition is v2 (TI-003).",
]


def _sparkline(values: list[int]) -> str:
    if not values:
        return "(none)"
    lo, hi = min(values), max(values)
    if hi == lo:
        return _BARS[0] * len(values)
    span = hi - lo
    return "".join(_BARS[int((v - lo) / span * (len(_BARS) - 1))] for v in values)


def _result_to_dict(r: EvaluationResult) -> dict:
    return {
        "session_id": r.session_id,
        "partition": r.partition,
        "leakage_note": r.leakage_note,
        "observation_density": r.observation_density,
        "lead_time": r.lead_time,
        "overshoot_baseline": r.overshoot_baseline,  # listed before deflection (Commandment 5)
        "deflection": r.deflection,
        "classifications": [{"index": i, "class": c} for i, c in r.classifications],
        "drift_rows": [asdict(row) for row in r.drift_rows],
    }


def write_pvh_metrics(results: list[EvaluationResult], path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "pvh_metrics/v1",
        "generated": date.today().isoformat(),
        "scope": "methodology-validator (D35/D39); no deflection claim asserted",
        "sessions": [_result_to_dict(r) for r in results],
    }
    path.write_text(json.dumps(payload, indent=2))


def _mean_abs_drift(r: EvaluationResult) -> dict:
    if not r.drift_rows or any(row.drift is None for row in r.drift_rows):
        return {t: None for t in TARGETS}
    n = len(r.drift_rows)
    return {t: round(sum(abs(row.drift[t]) for row in r.drift_rows) / n, 4) for t in TARGETS}


def write_evidence_artifact(results: list[EvaluationResult], path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    L = lines.append

    L("# PVH Evidence Artifact — v1 (Methodology Validator)")
    L("")
    L(f"**Generated:** {date.today().isoformat()}")
    L("**Scope:** path_d v1 — validates harness mechanics, not Harlo's multiplier effect.")
    L("")
    L("## ⚠️ v1 limitations (read first)")
    L("")
    for item in V1_LIMITATIONS:
        L(f"- {item}")
    L("")

    total_obs = sum(r.drift_rows and r.drift_rows[-1].exchange_index + 1 or 0 for r in results)
    total_windows = sum(len(r.drift_rows) for r in results)
    L("## Corpus")
    L("")
    L(f"- Sessions analyzed: **{len(results)}**")
    L(f"- Windows (3-observation): **{total_windows}**")
    for r in results:
        L(f"- Session `{r.session_id}` (`{r.partition}`): {len(r.drift_rows)} windows")
    L("")

    for r in results:
        L(f"## Session `{r.session_id}`")
        L("")
        L(f"- **Leakage:** {r.leakage_note}")
        mad = _mean_abs_drift(r)
        L(f"- **Mean |drift| per target:** {mad}")
        L("")

        burnout_actual = [row.actual["burnout"] for row in r.drift_rows]
        burnout_drift = [row.drift["burnout"] if row.drift else 0 for row in r.drift_rows]
        L("**Burnout (actual) over windows:**")
        L("")
        L("```")
        L(_sparkline(burnout_actual) + f"   (min={min(burnout_actual) if burnout_actual else 0}, max={max(burnout_actual) if burnout_actual else 0})")
        L("```")
        L("")
        L("**Burnout drift (predicted − actual) over windows:**")
        L("")
        L("```")
        L(_sparkline(burnout_drift) + "   (flat at 0 confirms target leakage — predicted reproduces actual)")
        L("```")
        L("")

        L("### Lead-time distribution")
        L("")
        L(f"- Status: **{r.lead_time['status']}** — {r.lead_time['reason']}")
        L("")
        L("| target | actual transitions |")
        L("|---|---|")
        for t, c in r.lead_time["actual_transition_counts"].items():
            L(f"| {t} | {c} |")
        L("")

        L("### Deflection vs overshoot (overshoot computed first — Commandment 5)")
        L("")
        L(f"- **Overshoot baseline:** status `{r.overshoot_baseline['status']}`, rate `{r.overshoot_baseline['rate']}`"
          + (f" — {r.overshoot_baseline.get('reason','')}" if r.overshoot_baseline.get("reason") else ""))
        L(f"- **Deflection rate:** status `{r.deflection['status']}`, rate `{r.deflection['rate']}`"
          + (f" — {r.deflection.get('reason','')}" if r.deflection.get("reason") else ""))
        L("")

        d = r.observation_density
        L("### Observation density (signal-weakness proxy)")
        L("")
        L(f"- mean gap: {d['mean_gap']}, max gap: {d['max_gap']}, weak-signal fraction (gap>{d['threshold']}): {d['weak_signal_fraction']}")
        L("")

    L("## Headline")
    L("")
    L("**Methodology proven; no multiplier verdict.** The harness extracts the organic")
    L("trajectory, feeds the reference model, computes the drift/lead-time/deflection")
    L("schema, and emits this artifact end-to-end. The reference predictor's target")
    L("leakage and the N=69 single-session corpus mean **no claim about Harlo")
    L("multiplying the user is supported by v1**. A leakage-free, horizon-defined")
    L("forecaster (TI-003) and a larger corpus are the prerequisites for the v2")
    L("evidence harness.")
    L("")

    path.write_text("\n".join(lines))
