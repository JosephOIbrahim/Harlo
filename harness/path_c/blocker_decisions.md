# Path C — Codec-Blocker Decisions Log

**Status:** Phase 5 deliverable &nbsp;|&nbsp; **Date:** 2026-04-28
**Authority:** records resolution of all five Mile-1-identified codec-blockers.

Recon §2 flagged five "codec-blockers" — fields/files that the
runtime tier handled with custom encodings, not USD-native types.
Mile 1 default policy: `string` sidecar at the persistence boundary
unless Phase 5 overrides per blocker. This document records the
Phase 5 status of each.

---

## CB-1 — Hex SDR codec on `TracePrim`

**Field:** `TracePrim.sdr` (`list[int]`, 2048-bit boolean SDR)
**Phase 1 default:** `string` sidecar named `sdr_hex` carrying the existing 512-char hex encoding (D8 pattern).

**Phase 5 status:** **CLOSED — sidecar absorbed in Phase 2.**
- Writer: `python/harlo/usd_lite/persistence/writer.py:107` calls `_set_string(prim, "sdr_hex", sdr_to_hex(t.sdr))`.
- Reader: `python/harlo/usd_lite/persistence/reader.py` decodes via `hex_to_sdr` on `sdr_hex` attribute.
- Crucible test: `tests/test_path_c/test_persistence_roundtrip.py::test_hex_sdr_codec_fidelity` round-trips a deterministic sparse pattern; bit-level equality.

**Typed-migration upgrade (deferred per D8):**
Future surgery may migrate to `int[]` (size 2048) or `bool[]`. Cost
trade-off: hex sidecar = ~512 chars per attribute vs typed array =
~16 KB per attribute in `.usda` text. Phase 5 default holds.

---

## CB-2 — Hex SDR codec on Hebbian masks (`TracePrim`)

**Fields:** `TracePrim.hebbian_strengthen_mask`, `TracePrim.hebbian_weaken_mask` (each `list[int]`, 2048-bit boolean)
**Phase 1 default:** `string` sidecars `hebbian_strengthen_mask_hex`, `hebbian_weaken_mask_hex` (D8 pattern).

**Phase 5 status:** **CLOSED — same mechanism as CB-1.** Writer lines 104–105; same Crucible test covers bit-level fidelity.

**Typed-migration upgrade:** same as CB-1.

---

## CB-3 — JSON-as-string blob on `TracePrim`

**Fields:** `TracePrim.co_activations` (`dict[str, int]`), `TracePrim.competitions` (`dict[str, int]`)
**Phase 1 default:** `string` sidecars `co_activations_json`, `competitions_json` carrying `json.dumps(..., sort_keys=True)` (D8 pattern).

**Phase 5 status:** **CLOSED — sidecar absorbed in Phase 2.**
- Writer: lines 101–102.
- Crucible test: `test_json_blob_codec_fidelity` round-trips a populated dict.

**Typed-migration upgrade (deferred per D8):**
Future surgery may model these as USD `relationship` types
(typed prim-to-prim links) plus a parallel `int[]` for counts. Cost:
requires migration script to resolve trace IDs → prim paths.
Dataclass dict-by-trace-id semantics are simpler. Phase 5 default
holds.

---

## CB-4 — JSON-as-string blob on `CompositionLayerPrim` and `IntakeHistoryPrim`

**Fields:**
- `CompositionLayerPrim.opinion` (`dict[str, object]`, free-form) — D8
- `IntakeHistoryPrim.answer_embeddings` (`list[float]`, vector) — D9

**Phase 1 default:** `string` sidecars `opinion_json`, `answer_embeddings_json`.

**Phase 5 status:** **CLOSED — sidecars absorbed in Phase 2.**
- Writer: line 126 (`opinion_json`), line 182 (`answer_embeddings_json`).
- Crucible test: `test_json_blob_codec_fidelity` covers `answer_embeddings`; `test_populated_stage_roundtrip` covers `opinion`.

**Per D8 / D9: deferred (NOT wontfix).** Future surgery may:
- `opinion` — investigate whether structurally untyped → permanent string sidecar OR partial typed migration of common fields. Recon flagged this as candidate "wontfix" but D8 keeps option open.
- `answer_embeddings` — migrate to `float[]` directly (recon flagged as cheap). D9 keeps deferred per Mile 1 codec-blocker uniform policy.

---

## CB-5 — Stale `data/stages/cognitive_twin.usda`

**Field:** Not a field — a stale on-disk artifact written by pre-rename Sprint 4 code.
**Phase 1 / Cmd 10:** Eviction in Phase 5.

**Phase 5 status:** **CLOSED — EVICTED 2026-04-28.**

### Eviction details

- File path: `C:\Users\User\Harlo\data\stages\cognitive_twin.usda`
- Pre-eviction size: 8,502 bytes, mtime 2026-03-30 12:45
- Eviction action: `rm data/stages/cognitive_twin.usda`
- Post-eviction state: file does not exist (verified)

### Eviction reason (per recon §1 + D6)

The file is a pre-rename artifact:
- Sublayer paths inside reference `C:\Users\User\Cognitive_Twin\...`, the OLD package path (commit `f830aeb` renamed `cognitive_twin → harlo` on 2026-04-03).
- No current writer in the codebase produces this file:
  - Sprint 4 `src/cognitive_stage.py:70` writes `data/stages/harlo.usda` (post-rename name).
  - Path C `python/harlo/usd_lite/persistence/writer.py` writes `data/stages/brain.usda`.
- F4 (Phase 5 Architect verification): zero references to `cognitive_twin.usda` in `src/`, `python/`, or any test under `tests/`.

### Git tracking note

`data/` is gitignored (`.gitignore:1`). `cognitive_twin.usda` was never tracked in git — `git ls-files data/stages/cognitive_twin.usda` returns nothing. The eviction is filesystem-level only; no git deletion entry appears in this commit.

### Sprint 4 stay-separate compatibility

Sprint 4 writes `harlo.usda` (different filename). The eviction does
not affect Sprint 4's data path. Tests under `tests/test_sprint4/`
do not reference `cognitive_twin.usda` (verified).

### Reference

- Recon §1: noted `cognitive_twin.usda` as orphan demo data.
- D6: `CONFIRMED-SHIPPED-AND-PRESENT-BUT-DORMANT` for Sprint 4; eviction of stale file scoped to Phase 5.
- Cmd 10: "Stale `data/stages/cognitive_twin.usda` evicted."
- Commit reference: package rename `f830aeb` (2026-04-03).

---

## Summary table

| ID | Codec-blocker | Phase 5 status | Default holds? |
|---|---|---|---|
| CB-1 | TracePrim.sdr → sdr_hex | CLOSED (Phase 2 absorbed) | Yes (per D8) |
| CB-2 | TracePrim.{strengthen,weaken}_mask → *_hex | CLOSED (Phase 2 absorbed) | Yes (per D8) |
| CB-3 | TracePrim.{co_activations,competitions} → *_json | CLOSED (Phase 2 absorbed) | Yes (per D8) |
| CB-4 | {CompositionLayerPrim.opinion, IntakeHistoryPrim.answer_embeddings} → *_json | CLOSED (Phase 2 absorbed) | Yes (per D8/D9) |
| CB-5 | data/stages/cognitive_twin.usda | CLOSED (EVICTED 2026-04-28) | n/a |

All five Mile-1-identified codec-blockers are now closed. Constitution Cmd 10 satisfied.

*End of codec-blocker decisions log.*
