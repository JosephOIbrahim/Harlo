# Mile 2 — Phase 5 Crucible Verification

**Role:** Crucible (adversarial verification, Commandment 7) &nbsp;|&nbsp; **Date:** 2026-04-28
**Phase:** 5 — Codec resolution + cognitive_twin.usda eviction &nbsp;|&nbsp; **Branch:** `harness-path-c`

---

## Verdict at a glance

**Phase 5 gate: ✅ PASS — all four Gate 5 criteria green.** Ready for Phase 6.

Phase 5 was deliberately small per session scope: F3 confirmed all five codec-blockers were absorbed in Phase 2, leaving only the eviction. Productivity floor (LR2 — 30 lines per phase) was waived per the override note ("phase may legitimately produce a small commit if F3 confirms no further codec work needed").

---

## Gate 5 criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | `data/stages/cognitive_twin.usda` no longer exists | ✅ | `ls data/stages/` — only `delegates`, `harlo.usda`, `test-stage.json` remain |
| 2 | No test references the deleted file | ✅ | Grep `cognitive_twin\.usda` across `tests/` and all `*.py` → 0 matches |
| 3 | Test baseline ≥ 1,170 (D19) | ✅ | `pytest tests/ --tb=no -q` → **1170 passed, 1 skipped, 0 failed, 0 errored** in 39.93s |
| 4 | Sprint 4 tests still pass (stay-separate held) | ✅ | `tests/test_sprint4/*` is part of the 1,170 baseline; no failures reported |

---

## Adversarial review

### Probe 1 — F3 confirmation completeness

Forge's F3 claim: all five codec-blockers absorbed in Phase 2. Crucible re-verifies by independent grep:

```
$ grep -nE 'sdr_to_hex|json\.dumps|hex_sdr|opinion_json|answer_embeddings_json|co_activations_json|competitions_json|hebbian.*mask_hex' python/harlo/usd_lite/persistence/writer.py
16:from ..hex_sdr import sdr_to_hex
101:    _set_string(prim, "co_activations_json", json.dumps(t.co_activations, sort_keys=True))
102:    _set_string(prim, "competitions_json", json.dumps(t.competitions, sort_keys=True))
104:    _set_string(prim, "hebbian_strengthen_mask_hex", sdr_to_hex(t.hebbian_strengthen_mask))
105:    _set_string(prim, "hebbian_weaken_mask_hex", sdr_to_hex(t.hebbian_weaken_mask))
107:    _set_string(prim, "sdr_hex", sdr_to_hex(t.sdr))
126:    _set_string(prim, "opinion_json", json.dumps(layer.opinion, sort_keys=True))
182:    _set_string(ih_prim, "answer_embeddings_json", json.dumps(ih.answer_embeddings, sort_keys=True))
```

All seven sidecar fields covered. Forge's F3 claim verified. ✅

### Probe 2 — F4 path-overlap independence

Forge's F4 claim: zero `/Brain` references in `src/`. Crucible re-verifies:

```
$ grep -rE '/Brain' src/   →  0 matches
$ grep -rE 'cognitive_twin\.usda' src/   →  0 matches
$ grep -rE 'cognitive_twin\.usda' python/   →  0 matches
$ grep -rE 'cognitive_twin\.usda' tests/   →  0 matches
```

No source code refers to the evicted file. Sprint 4's writer at
`src/cognitive_stage.py:70` writes `harlo.usda` (different filename).
F4 verified. ✅

### Probe 3 — eviction reversibility

The evicted file was an 8.5 KB pre-rename artifact. Could a future
session need to reproduce it?
- Sprint 4 code in `src/` is dormant but **could regenerate `harlo.usda` if invoked** (different filename; not a regression risk).
- The `cognitive_twin.usda` file's content was bound to the OLD package path (`C:\Users\User\Cognitive_Twin\...`) which no longer exists. Reproducing it would require explicitly setting up that old path — a no-go.

**Crucible verdict:** the eviction is genuinely safe and irreversible by design. No future session has a legitimate reason to reproduce the file.

### Probe 4 — accepting D15–D19 (F1)

Architect's `harness/path_c/07_DECISIONS_PHASE_4.md` documents D15–D19 as approved-via-gate-review. Crucible cross-references the gate review:

- `design/mile_2_phase_4_gate_review.md` §3 (Forge clarifications C1, C2, C3) — explicitly asks the human to approve as-authored.
- The session's mission states: "C1 approved as-authored", "C2 approved as-authored", "C3 approved as-authored" — pre-approved before this session's work.
- D15–D19 codify the approvals; no new design surface introduced.

**Crucible accepts F1.** D-block is now D1 through D19, all binding for future surgery.

### Probe 5 — Sprint 4 stay-separate compatibility under eviction

Forge claim: Sprint 4 doesn't reference the evicted file. Crucible's
adversarial check: would running `tests/test_sprint4/*` against a
fresh in-memory CognitiveStage produce a `cognitive_twin.usda`?

Looking at `src/cognitive_stage.py`:
- Default constructor uses `in_memory=False` and writes to `data/stages/harlo.usda` (line 70).
- Tests under `tests/test_sprint4/test_cognitive_stage.py` use `in_memory=True` (typical pytest fixture pattern), which calls `Usd.Stage.CreateInMemory()` at line 66 and never touches the filesystem.

Either way, `cognitive_twin.usda` is not produced or consumed. ✅

### Probe 6 — what's NOT covered?

Out of Phase 5 scope (correctly):
- **Backward eviction reversal** — design doesn't support undelete.
- **Other stale fixtures in `data/`** — only `cognitive_twin.usda` is the documented blocker; `harlo.usda` is Sprint 4's active output.
- **Schema-level codec changes** — D8/D9 keep sidecar default; typed-migration is post-Step-6 work (TI-002+ candidate, not yet filed).

These are correctly out of scope for this surgery.

---

## Phase 5 gate decision

**✅ PASS.** Phase 6 (test repair + final Crucible) may begin.

Crucible signs Phase 5.

*End of Phase 5 Crucible verification.*
