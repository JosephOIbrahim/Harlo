# NEXT — Resume point after the Phase 5A landing session

State captured at master `c42e82d` (+1 local `ee46533` parked) on 2026-05-24, end of an extended session that closed PR #10 and verified Phase 5A on the Mac Studio.

## Where we are

**Landed on master:**
- `f0ce331` — Phase 5A merge (PR #10): macOS bundle, intake CLI, biometric barrier, operator tooling
- `f074c6a` — verify dev-loop fixes (cargo `.cargo/config.toml`, readiness script yaml-availability, first_run fixture, schedule-test skipif, Makefile compliance-greps filters)
- `7a9fa8c` — py2app `install_requires` workaround for modern setuptools
- `c42e82d` — polish: Makefile venv auto-detect, agents/queue archive, SIGNING.md Python 3.14 note

**Verified locally:** `make verify` (no PYTHON= override needed — auto-detects `.venv314/`) → cargo 42/42, pytest 1365 passed / 11 skipped, compliance greps clean, `harlo doctor --strict` clean, signing-readiness 27/27 READY.

**Verified on CI:** Required checks all green. py2app builds Harlo.app on the macos-15 runner.

## What's parked

### CI workflow hardenings — abandoned this session

Two `macos-build.yml` improvements were drafted as a single commit on a local parked branch and then abandoned because the gh CLI OAuth App on `joe002` couldn't hold `workflow` scope (org policy or app config — `gh auth refresh -s workflow` completed the device-code authorize but server-side scopes stayed at `gist, read:org, repo`):

1. **Master push trigger** (paths-filtered) so regressions land-detect immediately instead of waiting for a PR or tag
2. **Graceful-skip** of the signing chain when Apple Developer secrets are absent, so `workflow_dispatch` + master pushes go green as build canaries without forcing secrets to exist first

The branch and commit have been deleted. If these turn out to matter later, recreating the 40-line YAML diff takes ~30 minutes — the bigger prereq is a different auth path (fine-grained PAT with Workflows: R+W, or browser edit at <https://github.com/JosephOIbrahim/Harlo/edit/master/.github/workflows/macos-build.yml>).

### Apple Developer secrets — 8 of them, none provisioned

Required for `macos-build.yml`'s sign / notarize / DMG steps. Until these land, tag pushes (`v*.*.*`) will skip the signing chain on the new graceful-skip path — i.e., release pipeline cannot ship signed artifacts.

**To resume:** work through `docs/APPLE_SECRETS_SETUP.md` (operator checklist, ~30–60 min, browser-heavy). Then `gh secret list` should show all 8 names; `gh workflow run macos-build.yml -f dry_run=false` validates end-to-end.

## What's freshly available

### `models/cognitive_predictor_v1.joblib` — regenerated this session

Was missing; XGBoost MultiOutputRegressor trained from `data/trajectories_10k.jsonl` (also regenerated). Training stats: 206 686 train / 25 836 val / 25 836 test rows, 111 features. Unblocks the four tests marked `requires_predictor_model`.

Both artifacts stay gitignored — the trajectories file is 229 MB (too big for raw git, and git-lfs setup is its own workstream), and the .joblib is downstream of it. Canonical regen path now lives in the Makefile:

```sh
make regen-predictor      # generates trajectories if missing, then trains the .joblib
make regen-trajectories   # just the data step
```

Predictor-dependent tests (`test_sprint*`, `test_recalibration`, the schedule e2e) skip cleanly when the .joblib is missing, so regen is opt-in.

### FAMILY-hours routing — investigated and fixed (was actually a migration bug)

Earlier this session, `tests/test_schedule/test_e2e_mcp_bridge.py::test_enrich_runs_full_exchange_with_clock_substitution` was marked `skipif(not predictor.exists())` under the assumption the failure was missing-artifact, then re-marked `xfail` after the predictor regen didn't fix it. Final investigation showed the failure had nothing to do with routing OR the predictor.

Real cause: `python/harlo/session/first_run.py`'s legacy migration skipped any top-level item where `target.exists()`. Engine bootstrap (via `schedule_migrate.migrate_inline`) writes a stub `schedule.usda` at `DATA_DIR/stages/` *before* `first_run` migration runs, so `first_run` saw `stages/` already existed and skipped it — leaving Joe's legacy 3,073-byte `schedule.usda` (with Saturday all-day FAMILY) unmigrated and the empty 198-byte stub in place. `evaluate_schedule` sees `timezone=""` and falls back to `WORK` (`src/schedule.py:132`), so the FAMILY → restorer override at `src/computations/compute_routing.py:91-92` never fires.

Fix: `first_run.py` now uses `shutil.copytree(src, dst, dirs_exist_ok=True)` for directory items so engine-bootstrap stubs get overwritten by legacy content. The first-run marker contract guarantees subdir contents at migration time are only auto-generated stubs, not user data — overwriting is safe. Top-level files (twin.db, observations.db, …) still preserve the don't-clobber semantics. Regression test added at `tests/test_session/test_first_run.py::TestFirstRun::test_migration_overwrites_engine_stubs`. The xfail marker on the schedule e2e test was removed — it passes now.

CLAUDE.md Rule 28 framing and `mcp_server.py:415` are correct as written; the documented "FAMILY → restorer" behavior IS what the engine implements when the schedule is loaded. The earlier "stale docs" framing was based on a misdiagnosis.

## Known fragilities (informational, not blockers)

- **macOS dev-loop on Python 3.14:** `.venv314` is 3.14; py2app's modulegraph 0.19.7 hits AST recursion on 3.14, so local `make build-macos` needs a separate 3.12 venv. CI is 3.12. Documented in `docs/SIGNING.md` "Local build environment" section.
- **macos-build's `build` job is `continue-on-error: true` for PRs.** Advisory canary by design — failures show in the UI but don't block merge. Strict on tag pushes.
- **`agents/queue/done/`** holds the completed 0001/0002/0003 task descriptors from PR #10. Harness globs non-recursively, so they're out of the dispatch loop.

## Next-session candidates, ranked

1. **Apple secrets** — 30–60 min, browser. Unblocks the full signing pipeline. Walkthrough: `docs/APPLE_SECRETS_SETUP.md`.
2. **Tag `v0.1.0`** — after #1 lands. Produces the first notarized stapled Harlo.app DMG attached to a draft GitHub release.
3. **Phase 5B (HealthBridge signing)** — register `com.harlo.healthbridge` in the portal + enable HealthKit capability + extend CI workflow with the second build job. `macos/HarloHealthBridge/` is already fully scaffolded; needs portal-side activation.
4. **Investigate the `test_injection` segfault on Python 3.14** — pre-existing flake during full `make verify` runs (USD + tqdm threading interaction). Doesn't affect CI (Python 3.12) or isolated test runs. Lower priority than the lanes above.

## Pointers

- Canonical signing runbook: [`docs/SIGNING.md`](docs/SIGNING.md)
- Operator checklist (this session's deliverable): [`docs/APPLE_SECRETS_SETUP.md`](docs/APPLE_SECRETS_SETUP.md)
- Phase 5B preview: `docs/SIGNING.md` § "Phase 5B preview (not yet active)"
