# LOG — append-only. Read before proposing. Dead ends are memory.

## Cycle 0 — FRAME / SKETCH
Contract written (SPEC.md). Seed champion = v2 doc. Mode: SOLO (one
dependency chain, no independent lines). Confidence at seed:
P1 .7 / P2 .6 / P3 .8 / P4 .5 / P5 .9.

## Cycle 1 — live MCP surface verification (Claude.ai session)
Verifier: tool-schema inspection + one status call. Closed the v2 appendix
unknown (signatures). Champion updates:
- Δ1 RESET LEVER: stage_reload reloads .usda only → reset = daemon stop →
  restore → daemon start with per-cell env. SQLite WAL/SHM must be in snapshot.
- Δ2 resolve_verifications is adjudication (verdicts per claim_id), not a flush.
- Δ3 recall drives v9 engine (exchange_index advances); QPE docstring does not
  → QPE preferred probe tool. No claim-submission MCP tool → Elenchus
  secondary scoring moves post-cells.
- Δ4 schedule.kind is a step-function confound for warm-full (FAMILY→restorer
  observed live). Cells must share one schedule block or pin /schedule/.
Free verifier: status exposes predictor flag + observations_logged →
per-cell config proof + write-leak detection.

## Cycle 2 — repo recon (Claude Code, read-only)
All six questions answered with file:line citations. Champion updates:
- Δ5 QPE is a PURE READ (no boosts, no Hebbian, no timestamp writes; decay is
  read-side math). Living-store problem half-dissolves for warm-mem.
  Note: unchanged strengths across probes are expected, not anomalies.
- Δ6 UTILITY MODE IS A STUB (router echoes ok, engine never touched; Rule 22
  fuzzing unimplemented). Dropped from design — daemon-lifecycle protocol
  routed around it. Filed as Harlo worklist candidate (privacy-adjacent).
- Δ7 Elenchus flush demoted gate → hygiene (restore makes pending state a
  constant across cells). >5 pending requires direct SQL (no enumeration tool).
- Δ8 Schedule pin mechanism verified: experiment sublayer at position 0
  (strongest); migrate_inline tolerates it; root-layer overs are stripped
  (don't use); MANDATORY teardown — position-0 layer persists silently.
Traps logged: env parse is literal == "1" ("true" silently disables) ·
launchd socket activation respawns daemon mid-restore (unload for window) ·
Claude Desktop MCP server also holds connections (disconnect during window).

## Cycle 3 — BUILD: experiments/memory-uplift/ (Claude Code)
14 files landed, engine code untouched, inert composers untouched.
Commits c3971f2..59d4596. Verifier ladder caught 3 bugs PRE-commit:
1. restore.sh relative-path hash verify after cd → absolutized early.
2. probe_lint.py mode=ro fails on cleanly-closed WAL db (SQLite err 14 — the
   shape of every clean snapshot) → temp-copy-and-checkpoint open, replays
   captured -wal without mutating the snapshot.
3. probe_lint.py crashed on lazily-created elenchus_pending absent → guarded.
P1 ACCEPTANCE PASSED on real data (282 sessions, integrity ok, no corruption).
Substitution logged honestly: shellcheck unavailable arm64 → bash -n (clean ×3).
Launchd pulse unit unloaded for test, re-armed and confirmed.

## Open items
- P2: probe construction (Cycle 4). Kill condition: pool < 12 after exclusion.
- Representation decision parked for architect: wordmark "AI-Assisted OS"
  vs README/repo/release "local-first AI coach" — four surfaces must agree.
- Worklist candidates (NOT this experiment): utility-mode stub wiring;
  Elenchus pending-claim enumeration tool.

## Dead ends
DEAD-END | stage_reload as the between-cell reset | reloads stage only;
  SQLite + hippocampus state untouched; superseded by daemon lifecycle (Δ1)
DEAD-END | utility mode as harness contamination boundary | stub — reports
  ok while DMN observes (Δ6)
DEAD-END | "frozen store" / flatten-to-base cold condition (v1) | superseded
  in v2 already; cold = MCP unmounted, daemon down
