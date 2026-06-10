# Temporal Models in Harlo

> Three clocks. Three jobs. One rule each.

## Why this doc exists

Harlo computes some things from integer counters, some from monotonic deltas, some from wall-clock timestamps. Each model has a job. Mixing them silently — using wall-clock for in-process velocity, or monotonic for cross-session decay — produces correctness bugs that look like flaky tests. This doc names the three models and the rule for each, so future code lands in the right one.

This is a **project-wide invariant**. It applies to both the v9 cognitive engine in `python/harlo/engine/` and the v8 memory/modulation/inquiry layer in `python/harlo/`.

---

## The three temporal models

| Model | Concrete API | Survives restart? | What it's for |
|---|---|---|---|
| **T1 — Exchange Index** | `int` counter, externally authored | Yes (persisted in stage) | Pure-function math. Replayable trajectories. Anywhere correctness must be reproducible from the same inputs. |
| **T2 — Monotonic** | `time.perf_counter_ns()` | **No** — restarts at 0 | In-process derivatives where a wall-clock jump (NTP, DST, sleep/wake) would corrupt math. Velocity, latency, within-session deltas. |
| **T3 — Wall-Clock** | `datetime.datetime.now(datetime.UTC)` | Yes | Persistence stamps, decay across sessions, TTL/staleness, week-bucketing, anything that crosses process boundaries. |

**Never substitute one for another.** Each model is the *only* correct choice for its job:
- T1 → T3 substitution makes trajectory replay non-deterministic.
- T2 → T3 substitution corrupts velocity on NTP correction.
- T3 → T2 substitution loses the value across restart.

---

## Rule by layer

### v9 — `python/harlo/engine/` (Cognitive State Machine)

**T1 only in the math layer.** Codified as **Commandment 3**: *exchange_index is the only temporal key.*

- All `python/harlo/engine/computations/*.py` are pure functions of the authored observation + previous state. Zero `import time`, zero `import datetime`.
- "Decay-like" behavior (energy decrement, burnout escalation) runs on integer modulo of `exchanges_without_break`, not seconds.
- Accumulators (`session_exchange_count`, `tasks_completed`, `adrenaline_debt`) are authored externally onto the observation; the math layer never increments them.

**T3 only at the persistence boundary.** Two surfaces:
- `python/harlo/engine/observation_buffer.py` — SQLite `created_at` column. **Pin to UTC ISO 8601 microseconds** (currently SQLite default, server-local).
- `python/harlo/engine/cognitive_stage.py` — USD save. The stage time axis is `Usd.TimeCode(exchange_index)` (T1, not T3). If calendar timestamps ever need to live in `.usda`, follow the **USD persistence rule** below.

### v8 — `python/harlo/` (Memory / Modulation / Inquiry / Brainstem)

**T3 for persistence and TTL.** Already correct in form — every `time.time()` call audited is a persistence stamp (`detected_at`, `consolidated_at`, `compiled_at`, `created_at`, `applied_at`) or a TTL window check. Wall-clock drift of ±seconds doesn't affect 48h–30d TTL math.

**The fix in v8 is format consistency, not correctness:**
- All `int(time.time())` writes should be replaced with UTC ISO 8601 microsecond strings on new code paths.
- Existing seconds-since-epoch ints are tolerated; migrate opportunistically.
- Sub-second precision is gained for free and matters for high-frequency stamps (e.g., `detector.py` cluster-detection runs).

**T2 for in-process derivatives.** Already correct in `python/harlo/modulation/allostatic.py` (`time.monotonic()`). Audit any future code that computes `now - prev_time` deltas — these must use T2.

**Hot path constraint (Rule 3):** Rust hot path measurements are not in scope of this doc. Hot recall <2ms targets predate the wall-clock/monotonic question — Rust uses its own `Instant`.

---

## T3 format spec (wall-clock)

**Canonical format:** UTC ISO 8601 with `Z` suffix, microsecond precision.

```
2026-05-08T17:53:30.718960Z
```

**Generation:**

```python
import datetime

def now_iso() -> str:
    return (
        datetime.datetime.now(datetime.UTC)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )
```

**Banned:**
- `datetime.utcnow()` — deprecated, returns naive datetime, ambiguous on serialize.
- `datetime.now()` (no tz arg) — local timezone, breaks on machines in non-UTC.
- `time.time()` for new persisted fields — use the helper above.
- Floats of seconds-since-epoch in new schemas — use the ISO string.

**Precision rationale:** Microsecond is what `datetime` natively round-trips, what Pydantic v2 serializes losslessly, and what the USD probe confirms is preserved end-to-end. Nanosecond is **not free** — ISO 8601 doesn't natively serialize nanos, and no Harlo computation has been demonstrated to need sub-microsecond cross-process precision. Sub-microsecond belongs in T2 (monotonic), where it's used and discarded in-process.

---

## T2 spec (monotonic)

**Canonical API:** `time.perf_counter_ns()` (returns nanoseconds since an arbitrary process-local epoch).

```python
import time

t_start = time.perf_counter_ns()
# ... work ...
delta_ns = time.perf_counter_ns() - t_start
```

**Rules:**
- Never serialize a `perf_counter_ns()` value to disk — it's meaningless after restart.
- If a value is *both* used in-process *and* persisted, capture both: T2 for the in-process delta, T3 (using the helper above) for the persisted stamp. Never derive one from the other.
- Use `time.monotonic_ns()` for second-level monotonic if you need clock resolution that's tied to system uptime; prefer `perf_counter_ns` for performance measurement.

---

## USD persistence rule

**Stage time axis = T1.** Time samples on Harlo USD attributes are keyed by `Usd.TimeCode(float(exchange_index))`. This is correct; do not change it.

**Calendar timestamps as USD attributes.** When a wall-clock value needs to live on a USD prim (it does not today, but may), the probe-confirmed lossless storage is:

```
custom string wallClockISO         = "2026-05-08T17:53:30.718960Z"
custom int64  wallClockEpochUs     = 1778262810718960
```

- The **string** is the human-readable canonical.
- The **int64** is the fast-comparison sibling.
- **Never use `double` for epoch microseconds.** USD's float64 representation truncates trailing zeros and approaches its ~15.95-digit safe-integer limit; current epoch-µs is already 16 digits.

Empirically verified by `harness/usd_precision_probe.py` (one-shot probe in `/tmp` on real USD 26.05, cp314): all three formats round-trip identically at today's magnitude; only `double` is forecast to lose low-order digits before 2058.

---

## Resolved decisions

### `wall_clock_delta` removed from `CognitiveObservation` (2026-05-08)

The field was authored in `python/harlo/engine/trajectory_generator.py` for synthetic training data but never authored in `python/harlo/engine/cognitive_engine.py._build_authored_observation` for live observations. Verification showed `_encode_observation` in `python/harlo/engine/train_predictor.py` did not reference the field, so the trained predictor never actually used it — but its presence on the schema invited future drift.

**Action taken:** field removed from `src/schemas.py` and `python/harlo/engine/trajectory_generator.py`. Folds into the queued `cognitive_predictor_v1.joblib` regeneration so synthetic data and predictor stay in sync.

**Restored invariant:** `CognitiveObservation` is now wall-clock-free, fully consistent with Commandment 3.

---

## Migration

**No `.usda` migration is required.** Existing stages (`data/stages/harlo.usda`, the two delegate sublayers, and the schema files) use `Usd.TimeCode(exchange_index)` exclusively. No calendar timestamps are stored in any `.usda` today.

**v8 SQLite tables** with `time.time()` integer stamps remain valid; new writes adopt the T3 ISO format. No backfill.

---

## Compliance check

```bash
# Forbidden in python/harlo/engine/computations/
grep -rE "import\s+(time|datetime)" python/harlo/engine/computations/   # MUST return 0 results

# Forbidden anywhere new
grep -rE "datetime\.utcnow\(\s*\)" src/ python/harlo/   # SHOULD return 0 results
grep -rE "datetime\.now\(\s*\)"   src/ python/harlo/    # naive now() — review each hit
```

---

*Harlo Temporal Models v1.0 — 2026-05-08*
