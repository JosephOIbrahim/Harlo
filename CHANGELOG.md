# Changelog

## v7.0.0 — USD Brain Housing + Brainstem + Hebbian Neuroplasticity

### Architecture

Complete v6 to v7 rewrite informed by 2026 frontier research (Titans, Mnemis, SSGM, REMem, HiMem, LoCoMo-Plus) plus neuropsych-informed cognitive profile calibration.

**5 phases completed:**

1. **USD-Lite Container** — 17 typed prim dataclasses, `.usda` serialization, LIVRPS composition, hex SDR encoding (512-char strings), float tolerance via `math.isclose()`
2. **Brainstem Translation** — Lossless adapter pairs with Hypothesis property-based fidelity proofs, Z-score surprise metric, dual-process routing (System 1/System 2), structured provenance (5 source types)
3. **Aletheia + Composition** — Already existed in v6, integrated with brainstem stage builder
4. **Cognitive Profile Intake** — Adaptive questionnaire, continuous [0.0, 1.0] scoring, personal multipliers, semantic ceiling detection (disengagement-based, not answer length). Incremental skills observer with cursor-based O(new_traces) processing
5. **Hebbian Neuroplasticity** — Dual-mask SDR evolution (`(base | strengthen) & ~weaken`), homeostatic plasticity [3%-5%], episodic context reconstruction, reconsolidation boost (user-retrieval gated), Aletheia training data pipeline (JSONL with full cognitive profile feature vector)

### 11 Gemini-reviewed patches applied

1. Surprise Z-score (ratio replaced with Z-score formulation, threshold 2.0)
2. Apoptosis twilight zone (reconstruction threshold clamped above apoptosis by 0.05)
3. Continuous scoring (intake uses [0.0, 1.0] floats, not buckets)
4. Merkle isolation (Hebbian deltas in [V] Variant layer, not destructive SQLite mutation)
5. Training data features (JSONL includes full cognitive_profile_features vector)
6. Semantic ceiling (disengagement detection, not answer length)
7. Dual masks (XOR toggle flaw fixed: `(base | strengthen) & ~weaken`, weaken wins)
8. O(1) log rotation (append-only + rotate-at-threshold, max 3 rotated files)
9. Hex SDR serialization (512-char hex strings, not 6KB text arrays)
10. Incremental skills observer (cursor-based, O(new_traces), ghost window safe)
11. Reconsolidation boost (retrieval boost to contributing traces, user-retrieval gated)

### Modules added

- `python/cognitive_twin/usd_lite/` — USD container format
- `python/cognitive_twin/brainstem/` — Lossless translation + metacognitive routing
- `python/cognitive_twin/hebbian/` — Neuroplasticity + reconstruction + training data
- `python/cognitive_twin/intake/` — Cognitive profile intake system
- `python/cognitive_twin/skills/` — Competence tracking observer
- `python/cognitive_twin/migrate_v7.py` — v6 to v7 migration

### Modules removed

- `python/cognitive_twin/bridge/` — Replaced by brainstem

### By the numbers

- 761 tests (720 Python + 41 Rust), all passing
- 20 test modules across all subsystems
- 17 typed prim dataclasses
- 5 MCP tools
- 33 inviolable architectural rules
- 5 source types for structured provenance

### Breaking changes

- Bridge module removed, replaced by brainstem with adapter-based translation
- USD-Lite stage format replaces raw dict-based brain state
- MCP server instructions updated (v6.0 to v7.0)
- CLI version string updated to 7.0.0
- Export format version bumped to 7.0.0

## v6.0.0 — Motor Cortex

Initial public architecture with Association Engine (Rust), Composition Engine, Aletheia verification, Inquiry/DMN, Motor Cortex with Basal Ganglia gating, and 33 inviolable rules.
