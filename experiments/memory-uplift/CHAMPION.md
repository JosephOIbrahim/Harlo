# CHAMPION — Memory-Uplift Experiment
*Current best protocol + exact recipe to reproduce and re-verify.
New work earns its place only by beating this on the SPEC contract.*

## Lineage
Seed champion: memory-uplift-experiment-v2-harlo-native.md.
Superseded on Δ1–Δ8 (see LOG.md). Key departures from v2:
daemon-lifecycle reset (not stage_reload) · utility mode dropped (stub) ·
QPE confirmed pure-read · Elenchus flush demoted to hygiene · schedule
pinned via position-0 sublayer with mandatory teardown.

## The protocol

### Pre-flight (once)
1. **All connection holders DOWN**: daemon stopped, launchd agent unloaded
   (socket activation respawns mid-restore otherwise), Claude Desktop / any
   MCP client disconnected from Harlo for the entire window.
2. *Hygiene (optional, recommended)*: enumerate `elenchus_pending` via SQL,
   adjudicate, submit through `resolve_verifications`. With full restore this
   is a constant across cells, not a confound — do it for clean coach context.
3. **Pin /schedule/**: `pin_schedule.py` inserts the experiment layer at
   subLayerPaths position 0. Verify via stage read-back. *(Fallback: run all
   six cells inside one schedule block and skip the pin.)*
4. **Snapshot**: `snapshot.sh` → SHA256 manifest. This is the universe every
   cell is born into.

### Cells (six, ABBA-counterbalanced, one wall-clock window)
Order: O-cold, F-cold, F-warm-mem, O-warm-mem, O-warm-full, F-warm-full.
For each: `run_cell.sh <cell> <snapshot>` — stop → restore → hash-verify →
start daemon with cell env (cold: daemon stays down) → capture pre.json →
**operator runs the subject Claude Code session** (model pinned per cell) →
capture post.json.

| Cell | Daemon | Env | Subject tool discipline |
|---|---|---|---|
| cold | DOWN, MCP unmounted | — | parametric only |
| warm-mem | up | PREDICTION_ENABLED=0, OBSERVATION_LOGGING=0 | **QPE primary** (pure read), recall permitted (advances exchange_index — acceptable), **no store, no coach** |
| warm-full | up | all "1" | full surface |

Per-cell checks: `observations_logged` unchanged across warm-mem (write-leak
detector) · boot banner on first status call is expected, tolerate it ·
any Fable fallback notice → trial DISCARDED, logged.

### Subject prompt (per cell, warm conditions)
Prompt B from the v2 doc: state retrieved-yes/no + summary, answer, note
whether the trace changed the answer; "not in memory" over guessing; never
store during the session.

### Scoring
1. **Primary**: human 0/1 retrieve-AND-apply per probe. Misapplied retrieval = 0.
2. **Secondary (post-cells only)**: route subject answers through Elenchus —
   via `store`/repo script AFTER all cells complete, alongside the lab-notebook
   write-back. Record VERIFIED / FIXABLE / SPEC_GAMED / UNPROVABLE; report
   SPEC_GAMED rate per model per condition. Never pass reasoning traces (Rule 11).

### Teardown (mandatory, same day)
`unpin_schedule.py` — the position-0 layer pins silently forever otherwise.
Re-arm the launchd agent. Confirm both via status/stage read-back.

### Report
Fill report_template.md. Two interaction terms, two separate verdicts.
If warm-full ≫ warm-mem, the value is the modulation layer — that is a
finding, not a failure. If warm-mem ≈ 0, recall the M3 trap: run one
multi-session task before concluding.

## Re-verify this champion
P1: snapshot→restore→hash-verify dry-run (passing as of c3971f2..59d4596).
P2: probe_lint.py exit 0 on probes.json.
P3/P4: pre/post status JSON per cell present, observations_logged stable in warm-mem.
