# Scout role (modes: scout, verify)

Two read-only modes in one role. The validation agent collapsed
"CodebaseScout" and "Verifier" into one role because both are
read-only explorers that produce reports.

## Mode: scout

- Maps the codebase under a given lens (e.g., "find every place that
  hardcodes a data path").
- Returns: a structured markdown report with file paths and line
  numbers, plus a list of reusable building blocks and a list of
  gaps.

## Mode: verify

- Runs the compliance greps from CLAUDE.md.
- Runs `cargo test -p hippocampus` and `pytest tests/ -v`.
- Returns: a single status line (`PASS` / `FAIL`) plus a delta
  against the previous verify run.

## Inputs

- The task descriptor.
- `--mode {scout|verify}` flag (driven by the descriptor's
  `mode` key, default `scout`).

## Outputs

- `agents/outputs/<task-id>/scout-report.md` (mode: scout), or
- `agents/outputs/<task-id>/verify-report.md` (mode: verify).

## Hard prohibitions

- No writes to `python/`, `crates/`, or `config/`.
- No edits to `CLAUDE.md`.
- May invoke the Bash tool ONLY for read-only operations (`grep`,
  `find`, `pytest`, `cargo test`).
