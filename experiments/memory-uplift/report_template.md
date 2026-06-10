# Memory Uplift — Results Report

**Run date:** `<YYYY-MM-DD>` · **Snapshot:** `<snapshot-id>` ·
**Subject:** `<n sessions per cell>`

## Design

3 cells × 2 measures. Cells: **cold** (no Harlo, MCP unmounted),
**warm-mem** (`PREDICTION_ENABLED=0 OBSERVATION_LOGGING=0` — memory recall
without engine telemetry), **warm-full** (production). Each cell restored
from the same snapshot so every run starts from identical state.

## 2×3 results

| Measure | cold | warm-mem | warm-full |
|---|---|---|---|
| **Probe accuracy** (VERIFIED probes answered correctly) | `__/__` | `__/__` | `__/__` |
| **SPEC_GAMED rate** (right answer, wrong question) | `__%` | `__%` | `__%` |

## Interaction terms

> Both terms get a one-line verdict even when null. A flat result is a
> result: fill it as cleanly as a positive one.

- **Memory × accuracy** (warm-mem − cold): `<verdict — e.g. "+0/12, no detectable uplift from recall alone">`
- **Telemetry × accuracy** (warm-full − warm-mem): `<verdict — e.g. "+1/12, within noise; engine adds no recall benefit in-window">`

## SPEC_GAMED rates

| cell | SPEC_GAMED | of total | note |
|---|---|---|---|
| cold | `__` | `__` | |
| warm-mem | `__` | `__` | |
| warm-full | `__` | `__` | |

One line on whether memory changed the *failure shape* (did warm cells
spec-game more, less, or differently than cold?): `<...>`

## Write-leak check

`run_cell.sh` asserts `observation_buffer` row count is unchanged for
warm-mem. Result: `<PASS / LEAK pre→post>`. cold: `<unchanged / anomaly>`.
warm-full growth: `<pre→post>`.

## Top uncontrolled validity threat

> The single most likely reason this result is wrong. Name one, concretely.

`<e.g. "Probe questions were authored after seeing the snapshot's
trace contents — accuracy may reflect probe-author leakage, not recall.
Mitigation next run: pre-register probes against a held-out snapshot.">`

## Verdict

`<one paragraph. If null: say so plainly and state what the null rules
out and what it doesn't. Do not manufacture a positive.>`
