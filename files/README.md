# Cognitive Twin v7.0 — Agent Team Kit (Final + 11 Patches)

## What's in this kit

This is the **final, doubly-reviewed** v7.0 agent team kit. Six patches from Gemini Deep Think plus five from Gemini Phase 1 Review have been applied to KICKOFF.md, AGENTS.md, and CLAUDE_ADDITIONS.md. The kit is ready to paste into Claude Code.

### All 11 Patches

| # | Patch | What Changed | Why |
|---|-------|-------------|-----|
| 1 | **Surprise Z-score** | `best_hamming / rolling_median` → `(best_hamming - rolling_mean) / max(rolling_std_dev, 1.0)` | Ratio blows up during cold-start when median is near zero. Z-score with std_dev floor is self-normalizing. |
| 2 | **Apoptosis clamp** | Reconstruction threshold = `max(apoptosis_threshold + 0.05, configured_threshold)` | Without clamp, a low-multiplier profile could have traces deleted before they qualify for reconstruction. |
| 3 | **Continuous scoring** | Intake multipliers from stepped buckets → continuous [0.0, 1.0] with linear interpolation | Stepped categories lose information. Continuous scoring is deterministic and preserves signal. |
| 4 | **Merkle isolation** | Hebbian deltas stored in `[V] Variant` layer, not destructive SQLite mutation | **CRITICAL.** Without this, Hebbian updates modify base SDRs, corrupting Merkle hashes, causing Crucible to loop indefinitely. |
| 5 | **Training data features** | JSONL row adds `cognitive_profile_features` (full float vector) alongside hash | Hash alone forces the model to memorize arbitrary strings. Feature vector enables continuous learning. |
| 6 | **Semantic ceiling** | Ceiling detection from "3 short answers" → semantic `user_disengaged: bool` | Short answers are valid for TERSE cognitive profiles. Length-based ceiling penalizes the users who need intake most. |
| 7 | **Dual masks (CRITICAL)** | `base XOR delta_mask` → `(base \| strengthen_mask) & ~weaken_mask` | **XOR toggle flaw:** reinforcing a bit already set to 1 flips it to 0. Set/clear is idempotent and directionally correct. |
| 8 | **O(1) log rotation** | FIFO line-by-line rewrite → append-only + rotate at threshold | FIFO rewrites 9,999 lines on every event — O(N) blocking I/O that violates zero-watt constraints. |
| 9 | **Hex SDR serialization** | 2048-int text arrays → 512-char hex strings + `__eq__` float tolerance | Text arrays are ~6KB per trace. Hex is 512 bytes. Orders-of-magnitude boot time difference at scale. |
| 10 | **Incremental skills observer** | Full trace scan → cursor-based incremental processing | Full scan blows 30-second ghost window at any non-trivial trace count. Cursor makes it O(new_traces). |
| 11 | **Reconsolidation boost** | Read-only reconstruction → retrieval boost on user-facing recall | Without boost, reconstructed traces decay to apoptosis immediately — death spiral. Boost gated to user retrieval only. |

### Architecture-Native Agent Rules

| Generic Rule | Twin Architecture Mapping | Why It Helps |
|---|---|---|
| Rule 2: Verify Every Mutation | **Basal Ganglia Gate** — default INHIBIT, must pass to proceed | Claude Code understands inhibition-default because it's implementing it |
| Rule 3: Circuit Breaker | **UNPROVABLE** — park with dignity, metadata, partial progress | "Stop and surface" becomes a first-class state, not a failure |
| Rule 5: Role Isolation | **Trace Exclusion (Rule 11)** — structural separation, not policy | Role boundaries feel structural because the same pattern is in the code |
| Rule 7: Adversarial Verification | **Crucible IS Aletheia** — blind verification, spec-gaming detection | The verifier pattern is the same one being built |

### Projected Scores Post-Execution

| Dimension | v6.0 | v7.0 (Phases 1-5) | Delta |
|---|---|---|---|
| Frontier AI Worthiness | 6 | **9** | +3.0 |
| Production Readiness | 7 | **8.5** | +1.5 |
| Biomimicry | 8 | **9.5** | +1.5 |
| AI Memory Frontier | 7.5 | **9.5** | +2.0 |

**Why Frontier AI hits 9:** Six implemented frontier contributions: Hebbian neuroplasticity, dual-process routing (Z-score), episodic reconstruction, structured provenance, verification training pipeline (with full feature vectors), and cognitive profile calibration. The intake system has no equivalent in the 2026 research landscape — it's an original contribution.

**Why Biomimicry hits 9.5:** Hebb's rule (1949) + Kahneman's System 1/System 2 + hippocampal fragment reconstruction + neuropsych-informed personal baseline + apoptosis/reconstruction lifecycle. The system doesn't just mimic brain structures — it calibrates to individual cognitive profiles.

**The remaining 0.5 to 10:** Real-world validation at scale, training the Aletheia classifier on accumulated data, publishing results.

---

## What's in this kit

| File | Purpose |
|------|---------|
| `KICKOFF.md` | **Paste into Claude Code.** Full spec with all 5 phases + all 6 Gemini patches. |
| `AGENTS.md` | **Replace** repo's `AGENTS.md`. Gate checklists with all patch-specific verification items. |
| `CLAUDE_ADDITIONS.md` | **Append** to repo's `CLAUDE.md`. Module boundaries, test commands, patch notes. |

## Setup (5 minutes)

1. **Replace AGENTS.md:**
   ```powershell
   copy AGENTS.md C:\Users\User\Cognitive_Twin\AGENTS.md
   ```

2. **Append to CLAUDE.md** — paste `CLAUDE_ADDITIONS.md` contents at the bottom.

3. **Create directories:**
   ```powershell
   cd C:\Users\User\Cognitive_Twin
   mkdir .agent-team\designs
   mkdir .agent-team\blockers
   mkdir data
   ```

4. **Open Claude Code** in `Cognitive_Twin`. Paste `KICKOFF.md`.

5. **Wait for Phase 1 design** → review → say "go".

## What happens

```
Phase 1: usd_lite/ (schema + dual masks + hex serialization + LIVRPS)     → Gate 1
Phase 2: brainstem/ (lossless + Z-score surprise + dual-process)          → Gate 2a-c
Phase 3: cutover (subsystems + structured provenance)                     → Gate 3a-d
Phase 4: skills/ (incremental) + intake/ + migration + bridge deletion    → Gate 4a-e
Phase 5: hebbian/ (dual masks) + reconstruction (reconsolidation) + data  → Gate 5a-d
```

## Expected outcomes

- **New modules:** `usd_lite/`, `brainstem/`, `intake/`, `skills/`, `hebbian/`
- **New MCP tools:** `twin_skills` (#6), `twin_intake` (#7)
- **New data:** `data/aletheia_training.jsonl` (with `cognitive_profile_features`)
- **New capabilities:** Dual-process routing (Z-score), episodic reconstruction (with reconsolidation boost), cognitive profile calibration, structured provenance, Hebbian neuroplasticity (dual-mask, Merkle-safe, O(1) training data)
- **Modified:** `session/`, `mcp_server.py`, `composition/`, subsystem adapters
- **Deleted:** `bridge/` (Phase 4)
- **Test target:** ≥ 550 tests
- **Untouched:** `crates/hippocampus/`, encoder, 33 rules, SQLite

## Token budget note

Five phases in one session is ambitious. Git tags at every gate passage. Restart from `v7-phase-{N}-complete` if context limits hit.
