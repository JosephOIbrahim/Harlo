# SPEC — Memory-Uplift Experiment (Fable 5 × Harlo)
*Contract. Nothing advances on unverified state. Append changes to LOG.md, never edit history.*

## Outcome
A contamination-controlled, executable experiment measuring whether Harlo's
memory layer gives a **disproportionate** uplift to a more capable model.
Quantity of interest is the interaction, reported separately for two claims:

    Δ_Fable − Δ_Opus    where Δ = score(warm) − score(cold)

- **arm 1 — warm-mem**: memory tools only (QPE primary; recall permitted),
  `PREDICTION_ENABLED=0`, `OBSERVATION_LOGGING=0`, no coach. → the **memory claim**.
- **arm 2 — warm-full**: full substrate (exchange loop, coach, routing,
  predictions). → the **substrate claim**.

A null result is a valid, reportable outcome. If arm 1 ≈ 0 the memory-tailwind
claim is false and the report says so plainly.

## Acceptance predicates (checkable)
- **P1 — State reset verified.** Restore yields hash-identical store state
  (twin.db + -wal + -shm, observations.db, data/stages/*.usda) before every
  cell. Verifier: SHA256 manifest in snapshot.sh / restore.sh.
  **STATUS: CLEARED** (dry-run on live store, daemon stopped, integrity ok).
- **P2 — Probe set sound.** 15–20 Q&A pairs; every probe resolves to a
  VERIFIED trace in the snapshot; tier-tagged (Hot/Warm), age-tagged
  (incl. near-apoptosis); zero trip-wire content (cybersecurity, bio/chem,
  distillation). Verifier: probe_lint.py against the snapshot copy.
  **STATUS: OPEN.**
- **P3 — Cell configs provable.** Kill-switch state logged per run via
  `status` capture (pre.json / post.json). Cold = daemon down, MCP unmounted —
  never a flattened stage. Env values are the literal strings "1"/"0".
  **STATUS: machinery landed (run_cell.sh).**
- **P4 — Contamination caught.** Fable safeguard-fallback notices logged;
  contaminated trials discarded. Write-leak detector: `observations_logged`
  must not advance during warm-mem probe runs. Utility mode is NOT used
  (stub — see LOG Δ6).
- **P5 — Report forced honest.** report_template.md requires the 2×3 table,
  both interactions with one-line verdicts, SPEC_GAMED rates, and the top
  uncontrolled validity threat. A null fills it as cleanly as a positive.

## Out of scope
- Running M2 (write-side) / M3 (multi-session) arms in the MVP — designed,
  not executed.
- Any HealthKit / Wave-2 scope.
- Repositioning or marketing conclusions (those live in the outcomes table,
  post-data).
- Fixing the utility-mode stub or claim-enumeration gap (separate worklist).

## Falsification conditions (kills the APPROACH, not the hypothesis)
- Decay drift across the run window approaches the effect size — lazy decay
  is wall-clock math at read; ABBA + one tight window is the mitigation.
  If insufficient, the design cannot resolve the question.
- VERIFIED probe pool after trip-wire exclusion < 12 → power is decorative.
  Stop; rescope probes before running any cell.
- Fable fallback fires on a large fraction of probes → Fable cells are not
  measuring Fable. Discard and reconsider probe content.

## Sampling caveat (carry into the report verbatim)
Fable serves at temperature 1.0, thinking always-on. We measure the models
**as served**. Deltas below the noise floor are not findings.
