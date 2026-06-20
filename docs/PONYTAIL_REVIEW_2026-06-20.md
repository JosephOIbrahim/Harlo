# Ponytail Over-Engineering Review — 2026-06-20

> **STATUS — Tier 1 APPLIED 2026-06-20.** 35 files changed, **+54 / −740 (net −686 lines)**,
> 3 files deleted (`modulation/utility_mode.py`, `modulation/burst_verifier.py`,
> `daemon/connection_pool.py`). Coupled tests updated. Also pulled in the coupled Tier-2
> item **I9** (`globally_enabled` field) since it must be removed together with I8 — its
> short-circuit was a provable no-op (flag was never toggled to False). Tier 2/4/5 NOT applied.
>
> Verification: `cargo test -p hippocampus` → 41 passed / 0 failed (43 baseline − 2 orphaned
> reflex tests). `py_compile` clean on all 31 edited Python files. Import sweep of all edited
> production modules → OK. Repo-wide grep → zero dangling references to any deleted symbol.
> Behavior-preserving refactors (`gate()` LOCKED/INHIBIT, encoder `_embedding_to_sdr`,
> `recover_temp`) reviewed by diff and confirmed equivalent.
> ⚠️ The Python **pytest suite could not be run** in this environment (pytest not installed;
> `harlo` not pip-installed). Run `pytest tests/` in your configured env as the final gate.

> **STATUS — Tier 2 + Tier 4 (M3) APPLIED 2026-06-20** (follow-up to PR #19). 4 files, **−75 lines**.
> - **C1** `MerkleTree.get_proof` deleted — its only caller (the stage wrapper) went in Tier 1, so it is now confirmed dead.
> - **R5 (partial)** `bytes_to_sdr` + its roundtrip test deleted (dead deserialization; `sdr_to_bytes` kept — production). **`hamming_distance` KEPT** — it backs real encoder-locality contract tests (similar→close, different→far, identity→0); deleting it would cost coverage, not just lines. Deliberate deviation from the Tier 2 line item.
> - **M3** `apply_modulation` + its test deleted. Rule 10 (anchor gain = 1.0) stays covered by `compute_gain` tests (test_profile) and the production `compute_injection_gain` tests (test_cogexec) — no coverage lost.
> - **Tier 5 (D3)** still parked — needs a roadmap call (will `agents/harness.py` adopt the second socket API?). Untouched.
> Verification: `cargo test -p hippocampus` 40/0; py_compile + import + dangling-ref grep clean.

Scope: **over-engineering and unnecessary complexity only.** Not correctness,
security, or performance (route those to a normal review). Findings list what to
cut; this report does **not** apply fixes.

## How this was produced

1. Six parallel review agents swept the codebase (`python/harlo/**`, `crates/hippocampus/**`)
   and produced **55 raw findings** (~965 lines proposed for removal).
2. **55 read-only skeptic agents** then each tried to *refute* one finding —
   full-repo caller search including PyO3 `#[pyfunction]` exposure, MCP tool
   registration, Click commands, `__all__` re-exports, `getattr`/string dispatch,
   plus dependency-availability and the ponytail self-check exemption.
3. Verdicts: **CONFIRMED** (verified safe), **REFUTED** (real caller / contract /
   wrong replacement — keep it), **UNCERTAIN** (park).

**Result: the verification pass invalidated ~46% of the raw proposals.** Most
deaths were claims that collided with public-API `__all__` contracts, deliberate
performance optimizations, wrong line ranges, or wiring debt misread as redundancy.

| Bucket | Count | Lines |
|---|---|---|
| Tier 1 — CONFIRMED, cut now | 34 | ~469 |
| Tier 2 — CONFIRMED, apply with a condition | 3 | ~44 |
| Tier 3 — REFUTED, keep (with reason) | 16 | 0 |
| Tier 4 — judgment call | 1 | ~28 |
| Tier 5 — UNCERTAIN, park | 1 | ~85 if dead |
| **Total verified-removable (Tier 1+2)** | **37** | **~513** |

---

## Tier 1 — CONFIRMED. Safe to cut now.

Verified zero real callers (or proven-equivalent shrink). Format:
`location: tag action. → lines`

### Dead code — delete

```
modulation/utility_mode.py:1-13        delete: Phase-6 stub; real enter/exit live in inquiry/timing.py.   → 13
modulation/burst_verifier.py:1-30      delete: Phase-6 stub; verify_burst/reject_burst zero callers.       → 30
modulation/detector.py:447-484 (+L19)  delete: legacy detect_pattern + _PATTERNS; prod uses detect_all.    → 39
modulation/detector.py:434-444         delete: clear_patterns, test-only.                                  → 11
modulation/profile.py:132-158          delete: save_profile, zero callers; config is hand-edited YAML.     → 27
brainstem/__init__.py:51               delete: "compose" in __all__ — never defined; import errors.        → 1
brainstem/escalation.py:8              delete: unused `from datetime import datetime, timezone`.            → 1
elenchus/depth.py:61-63                delete: get_max_depth; cap hard-coded inline in protocol.py.         → 3
inquiry/engine.py:378-387              delete: get_stats, zero callers anywhere.                            → 10
inquiry/crystallization.py:87-92       delete: get_decay_rate; value stored but never retrieved.           → 6
inquiry/apoptosis.py:54-65             delete: remaining_hours; should_delete() is the used path.           → 12
inquiry/dmn_window.py:100-114          delete: to_teardown_context; SessionManager builds its own ctx.      → 15
inquiry/consent.py:70-76               delete: disable_all/enable_all, zero callers (see I9 — apply both).  → 7
composition/merkle.py:103-112          delete: verify_proof, zero callers; proof path never integrated.     → 10
composition/stage.py:81-86             delete: MerkleStage.get_proof wrapper, zero external callers.        → 6
motor/consent.py:90-92                 delete: is_locked one-liner; inline `== ConsentLevel.LOCKED`.        → 2
daemon/connection_pool.py:1-71         delete: whole module; only tests/test_tactical imports it.          → 71
injection/__init__.py:155-162          delete: get_by_session + its test; zero production callers.          → 8
encoder/semantic_encoder.py:170-216    delete: __main__ demo; test_semantic.py genuinely covers it.        → 47
crates/.../store.rs:38-44              delete: ConsolidationReport struct, never constructed.               → 7
crates/.../graph.rs:57-74             delete: get_all_neighbors (OR-edge variant), zero callers.           → 18
crates/.../reflex.rs:106-122          delete: increment_hit_count + record_success, not PyO3-exposed.      → 17
crates/.../reflex.rs:124-164          delete: decompile/list/invalidate_reflex, not PyO3-exposed.          → 41
```

> Note on `encoder/semantic_encoder.py:170-216`: the ponytail self-check exemption
> was checked — deletion is allowed *only because* `tests/test_encoder/test_semantic.py`
> reproduces every assertion (determinism, sparsity, paraphrase Hamming distances).
> It is redundant, not the only check.

### Shrink — same logic, fewer lines

```
brainstem/epistemological_bypass.py:44   shrink: `in _INQUIRY_SOURCES or == "inquiry"` → just `in _INQUIRY_SOURCES` ("inquiry" is a member). → 1
brainstem/amygdala.py:97-136             shrink: drop duplicate "response"/"outcome" + unread matched_keywords (keep matched_safety/consent). → 6
inquiry/rupture_repair.py:70-74          shrink: is_topic_blocked byte-identical to should_offer_stop; repoint engine.py:137, delete method. → 5
motor/basal_ganglia.py:143-152           shrink: side_effects branch can never fire (config key never set, side_effects never populated) → `return True, None`. → 9
motor/basal_ganglia.py:266-272 (+L23)    shrink: GateDecision.ESCALATE — executor treats it identically to INHIBIT; drop enum + branch. → 8
motor/basal_ganglia.py:252-264           shrink: gate() recomputes effective_consent_level already done in _check_consent; collapse LOCKED check. → 10
daemon/dmn_teardown.py:132-146           shrink: single-element candidates list + for-loop → one path + try/unlink. → 3
encoder/semantic_encoder.py:85-145       shrink: encode_batch re-inlines encode's projection→top-k→pack; extract _embedding_to_sdr (onnx_encoder already has it). → 17
crates/.../encoder.rs:33-41             shrink: hand-rolled `impl Default for Metadata` → `#[derive(Default)]` (all fields Default). → 8
composition/layer.py:9                    shrink: drop unused `field` from dataclasses import. → 0
composition/resolver.py:9                 shrink: drop unused `field` from dataclasses import. → 0
```

---

## Tier 2 — CONFIRMED, but apply with the noted condition.

```
composition/merkle.py:83-101   MerkleTree.get_proof — the lone caller is stage.py's get_proof wrapper, itself dead (Tier 1).
                               DEAD ONCE you delete composition/stage.py:81-86. Delete the cluster (merkle.get_proof +
                               stage.get_proof + verify_proof) together. → ~19
inquiry/consent.py:33,51-52    globally_enabled field + is_allowed short-circuit. Dead, BUT only orphaned correctly if you
                               ALSO delete disable_all/enable_all (Tier 1 I8) which write it. Apply I8 + I9 as one edit. → 3
crates/.../encoder.rs         R5 line range was WRONG: 144-170 includes sdr_to_bytes (161-163), which IS production
                               (query.rs store_new_trace → py_store_trace). Delete ONLY hamming_distance (146-158) and
                               bytes_to_sdr (166-170); KEEP sdr_to_bytes. → ~22
```

---

## Tier 3 — REFUTED. Do NOT cut. (Recorded so they aren't re-flagged.)

Each of these *looked* like dead code or bloat and is not. Reasons are the value here.

```
modulation/profile.py:47-95     KEEP _parse_yaml_simple. PyYAML is NOT in pyproject — yaml.safe_load would crash offline.
                                Real issue is dependency hygiene, not over-engineering. (And the fallback mis-parses lists —
                                a correctness bug for the normal-review pass, out of scope here.)
modulation/state.py + state_store.py  KEEP both. Not redundant: state.py encodes ADR-0001's 5-min RED freshness; state_store.py
                                uses 30-min. Real issue is WIRING (apply_to_session_state never called in the motor path), not duplication.
modulation/gain.py:30-57        apply_modulation has no prod caller, BUT proposed replacement compute_injection_gain is a
                                different function (dict→dict vs scalar). See Tier 4 — judgment.
modulation/detector.py:40-51    KEEP hand-written to_dict. dataclasses.asdict would leak the large `messages` field; the
                                selective serialization is intentional and asserted by test + 4 MCP/HTTP callers.
biometric_prior/server.py:33-49 KEEP BiometricStore Protocol + InMemoryStore. Both used as type annotations + a real HTTP
                                contract-test fixture; deliberate phased architecture.
brainstem/escalation.py:17      KEEP composition_to_layers. Public API in __all__, exercised by a round-trip property test.
elenchus/protocol.py:30-59      KEEP _describe_flaw. Generates targeted flaw strings fed into the LLM revision prompt; not
                                interchangeable with detect_spec_gaming (that path returns SPEC_GAMED, not FIXABLE).
elenchus/states.py:64-80        KEEP hand-rolled to_dict. asdict leaves the enum unserializable; JSON-safe output is the contract.
elenchus_v8/__init__.py:159-209 KEEP limit=None path. Documented public API ("None = unlimited") with explicit test.
inquiry/engine.py:289-314       KEEP synthesize. Public API via __all__ + ARCHITECTURE.md (backward-compat shim).
inquiry/engine.py:316-324       KEEP prepare_traces_for_dmn. Public API via __all__.
inquiry/__init__.py:17-18,26-27 KEEP the aliases. They ARE the public API surface for the above.
inquiry/rupture_repair.py:35,55 KEEP _topic_counts dict. O(1) cache for hot-path gating; recompute would be O(n).
motor/scope.py:87               KEEP inline `import json`. Style nit (0 lines), not over-engineering; matches a repo pattern.
migrate_v7.py                   KEEP whole module. Retained v6→v7 migration path per harness/path_c/03_HANDOFF.md + CHANGELOG.
crates/.../reflex.rs:24-37      KEEP UnverifiedReflexError. Live path enforcing Rule 12, PyO3-surfaced, tested both sides.
crates/.../encoder.rs:113-142   KEEP enforce_sparsity early return. Deliberate perf optimization (skips alloc + bitvector scan).
```

---

## Tier 4 — Judgment call.

```
modulation/gain.py:30-57   apply_modulation is genuinely test-only (one caller: test_apply_modulation_preserves_clean).
                           Deletable IF you accept dropping that test, which asserts the Rule 10 anchor-gain=1.0 safety
                           property. Harmless if left. Your call: ~28 lines + its test, or keep as a documented invariant.
```

---

## Tier 5 — UNCERTAIN. Park, revisit.

```
daemon/socket_activation.py:161-245   Second "source-label" socket API (acquire_listen_socket + 3 helpers, ~85 lines).
                                      Test-only today, but in __all__ and the module docstring says agents/harness.py
                                      should adopt it in a follow-up. If that follow-up is cancelled → CONFIRMED dead (~85).
                                      If not, it's staged future code. Decide the follow-up first.
```

---

## Recommended apply order

1. **Tier 1 deletes** (lowest risk, ~360 lines) — pure dead code, no behavior change.
2. **Tier 1 shrinks** (~67 lines) — verify the one motor refactor (basal_ganglia 252-264 uses a
   `"LOCKED" in reason` string match) against `cargo test`/`pytest` motor + compliance suites.
3. **Tier 2 clusters** (~44 lines) — apply each as one atomic edit (merkle/stage/verify_proof together;
   I8+I9 together; R5 with the corrected range).
4. Decide **Tier 4** and **Tier 5** explicitly; leave the Tier 3 reasons in place so a future sweep
   doesn't re-propose them.

**net: ~513 lines verified-removable (Tier 1 + Tier 2); up to ~626 if Tier 4 + Tier 5 resolve toward deletion.**

Two non-scope items surfaced during verification, flagged for a *normal* review (NOT acted on here):
`modulation/profile.py` YAML fallback mis-parses lists (correctness), and the dual modulation-state
stores are a wiring gap (`apply_to_session_state` never called on the motor path).
