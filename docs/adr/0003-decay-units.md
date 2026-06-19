# ADR-0003 — Warm-tier decay unit is DAYS

Status: Accepted (2026-06-10). Resolves Δ9 (the implicit seconds reading).

## Context
`compute_lazy_decay` (Rust + its Python mirror) applied λ=0.05 to
`dt = now − created_at` in raw Unix **seconds** → a 13.9-**second** half-life,
~92-second time-to-ε (ε=0.01). Any warm trace older than ~92 s was deleted by
apoptosis; the warm tier could never accumulate. No retention horizon was
documented, but every other timescale in the system is days/weeks (S5 48h–30d,
S7 30-day crystallization, S3 90-day). A 14-second core memory is the outlier.

## Decision
The elapsed term is **DAYS**: `dt = (now − created_at) / 86_400`. λ=0.05 is a
**per-day** rate → **13.9-day half-life**, ε at ~92 days. Applied identically in
`crates/hippocampus/src/decay.rs` (which feeds BOTH recall and apoptosis) and the
Python mirror `python/harlo/encoder/_compute_lazy_decay`.

## Consequences
- A day-old trace survives at strength ≈ 0.95 — coherent with S5/S7/S3.
- **No data migration.** Strength is computed read-side from stored
  (`initial_strength`, `decay_lambda`, `created_at`, `boosts_json`); only the
  interpretation changed. No persisted `strength` column exists.
- Regression locked by `decay::tests::test_decay_unit_is_days` and
  `tests/test_decay_units.py` (both fed realistic Unix epochs — the case the
  prior 1,140 tests never exercised).
- Flagged, NOT changed: `python/harlo/compaction/__init__.py` variant weighting
  shares the same seconds-dt shape but is a separate subsystem — future decision.
