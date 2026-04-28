# Mile 2 — Phase 5 Codec Resolution + Eviction Design

**Role:** Architect &nbsp;|&nbsp; **Date:** 2026-04-28
**Authority:** subordinate to gate-approved C1/C2/C3 + D-block (D1–D14, D15–D19). No new design.

---

## 1. F3 — codec audit (confirmation only)

**Question:** is there codec-blocker work remaining beyond `cognitive_twin.usda` eviction?

**Answer: NO.** Phase 2 absorbed all five codec-blocker fields into the writer; the migration script smoke test (Phase 4) reported 81 codec conversions on `data/hebbian_seeded.usda` (16 traces × 5 codec fields per trace + 0 layers' opinion + 1 IntakeHistory). All six codec-blocker boundaries are covered:

| Codec-blocker | Where handled | Evidence |
|---|---|---|
| Hex SDR (`TracePrim.sdr`) | `writer.py:107` `_set_string(prim, "sdr_hex", sdr_to_hex(t.sdr))` | `test_hex_sdr_codec_fidelity` round-trips the bit pattern |
| Hex SDR mask (`hebbian_strengthen_mask`) | `writer.py:104` | Same |
| Hex SDR mask (`hebbian_weaken_mask`) | `writer.py:105` | Same |
| JSON blob (`co_activations`) | `writer.py:101` `_set_string(prim, "co_activations_json", json.dumps(..., sort_keys=True))` | `test_json_blob_codec_fidelity` |
| JSON blob (`competitions`) | `writer.py:102` | Same |
| JSON blob (`opinion`) on CompositionLayerPrim | `writer.py:126` | `test_populated_stage_roundtrip` |
| JSON blob (`answer_embeddings`) on IntakeHistoryPrim | `writer.py:182` | Same |

**No additional codec-blocker work for Phase 5.**

## 2. F4 — Sprint 4 path-overlap check (confirmation only)

**Question:** does Sprint 4 (`src/cognitive_stage.py`) read or write paths under `/Brain` that Path C would also touch?

**Answer: NO.** Empirical confirmation:

- `grep` of `src/cognitive_stage.py` shows it writes to: `/state`, `/state/momentum`, `/state/burnout`, `/state/energy`, `/state/injection`, `/state/allostatic`, `/routing`, `/sessions`, `/delegates`, `/prediction`, `/memory`, `/projects`. **All top-level scopes; no `/Brain` ancestor.**
- `grep -rE '/Brain' src/` returns zero matches.
- Sprint 4's output file is `data/stages/harlo.usda` (`cognitive_stage.py:70`). **NOT `cognitive_twin.usda`.** Path C's persistence layer writes to `data/stages/brain.usda` per Phase 2 implementation plan §1.

**Path-overlap = ZERO.** Eviction of `data/stages/cognitive_twin.usda` cannot break Sprint 4.

## 3. Eviction target

`data/stages/cognitive_twin.usda` (8,502 bytes, last modified 2026-03-30) is **stale demo data**:

- Pre-rename artifact (file exists from before package was renamed `cognitive_twin → harlo`)
- Sublayer paths inside reference `C:\Users\User\Cognitive_Twin\...` (the OLD package path)
- No current writer in the codebase produces this file (Sprint 4 now writes `harlo.usda`; Path C writes `brain.usda`)
- Recon §1 flagged it as orphan; D6 confirmed; gate review §1 confirmed eviction scope is Phase 5

**Phase 5 Forge action:** delete the file. Log in `harness/path_c/blocker_decisions.md`. Confirm no test references the file.

## 4. Phase 5 deliverables

| Path | Action | Authored by |
|---|---|---|
| `design/mile_2_phase_5_codec_eviction.md` | Created (this doc) | Architect |
| `harness/path_c/07_DECISIONS_PHASE_4.md` | Created (F1, D15–D19) | Architect |
| `data/stages/cognitive_twin.usda` | DELETED | Forge |
| `harness/path_c/blocker_decisions.md` | Created (eviction log) | Forge |
| `forge/mile_2_phase_5_report.md` | Created | Forge |
| `verify/mile_2_phase_5_crucible.md` | Created | Crucible |

## 5. Crucible Gate 5 criteria

| # | Criterion | How verified |
|---|---|---|
| 1 | `data/stages/cognitive_twin.usda` no longer exists | `os.path.exists` check |
| 2 | No test references the deleted file | grep test files for the literal path |
| 3 | Test baseline ≥ 1,170 (D19) | `pytest tests/ --tb=no -q` |
| 4 | Sprint 4 tests still pass (stay-separate held) | `pytest tests/test_sprint4/` subset |

## 6. Architect handoff to Forge

Forge:
1. Delete `data/stages/cognitive_twin.usda`.
2. Author `harness/path_c/blocker_decisions.md` with the five Mile 1 codec-blocker entries closed.
3. (No additional codec work — F3 confirmed.)

*End of Phase 5 design.*
