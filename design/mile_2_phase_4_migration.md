# Mile 2 — Phase 4 Migration Script Design

**Role:** Architect &nbsp;|&nbsp; **Date:** 2026-04-28
**Authority:** subordinate to Phase 1 design + 03_HANDOFF Phase 4 + D14 baseline.

---

## 1. Goal

Migrate USD-Lite text-format `.usda` files (the existing
`usd_lite.serializer` output) to real OpenUSD `.usda` files (the
Path C persistence layer output). Read-tolerant on input;
idempotent on already-migrated files.

## 2. Algorithm

Two-phase format detection, then dispatch.

### 2.1 Format detection

Two unambiguous signatures distinguish the formats:

- **Old USD-Lite format:** `#usda 1.0` header followed by
  `def BrainStage "Brain"` block (verbatim what
  `usd_lite/serializer.py` emits).
- **New real-USD format:** `#usda 1.0` header followed by
  `def BrainStage "Brain"` (the prim defined under
  `/Brain` typed `BrainStage`). **Same surface header**, but
  the prim has the `harlo` schema's typed attributes.

Disambiguation: try opening the file with `pxr.Usd.Stage.Open`.
If the stage opens successfully and `/Brain` resolves to a typed
`BrainStage` prim with at least one Harlo-namespaced attribute
(e.g., `/Brain/CognitiveProfile/Multipliers.surprise_threshold`),
it's the new format. Otherwise (stage opens but no typed
`BrainStage` *or* parsing succeeds via the old regex parser),
it's the old format.

### 2.2 Dispatch

```python
def migrate(input_path: str, output_path: str | None = None,
             dry_run: bool = False) -> MigrationReport:
    """
    Returns MigrationReport with:
      - input_format: "old" | "new" | "unknown"
      - output_path: str (defaults to input_path + ".migrated.usda")
      - prims_migrated: dict[typeName, int]
      - codec_conversions: int
      - dry_run: bool
      - error: str | None
    """
```

Dispatch logic:
- If new format: no-op (idempotent). Returns report with
  `input_format="new"` and `prims_migrated={}`.
- If old format: parse via `usd_lite.serializer.parse`, count
  prims by walking the resulting `BrainStage`, write via
  `persistence.write(stage, output_path)`.
- If neither: returns `input_format="unknown"` with an error
  message; non-zero exit code if invoked from CLI.

Idempotence: running the script on its own output produces the
same result (input_format detected as "new", no-op, exit 0).

### 2.3 CLI

```
python -m harlo.migrate_path_c INPUT [--output OUTPUT] [--dry-run] [--report REPORT_JSON]
```

- `INPUT` (required): old or new format `.usda` file
- `--output` (default: `<input>.migrated.usda`): where to write the new format
- `--dry-run`: detect format and count prims, don't write
- `--report`: write a JSON `MigrationReport` to this path

Exit codes:
- 0: success (including no-op for already-migrated)
- 1: input format unrecognized
- 2: parse error
- 3: write error

## 3. Crucible Gate 4 criteria

| # | Criterion | How verified |
|---|---|---|
| 1 | Round-trips `data/hebbian_seeded.usda` (representative existing capture) without data loss vs current `usd_lite.parse` output | `test_migrate_hebbian_seeded` — parse old format, migrate, read new format, compare to original parse output via `BrainStage.__eq__` |
| 2 | Idempotent: running the script on its own output produces an identical stage | `test_migrate_idempotent` — migrate the migration output; assert `input_format == "new"` and `prims_migrated == {}` |
| 3 | 1,164 baseline preserved | `pytest tests/ --tb=no -q` |

## 4. Test plan (Forge implements)

`tests/test_migrate_path_c/`:
- `__init__.py`
- `test_migration.py`:
  - `test_migrate_hebbian_seeded` — Crucible Gate 4 criterion 1
  - `test_migrate_idempotent` — Crucible Gate 4 criterion 2
  - `test_migrate_unknown_format` — invalid input → error
  - `test_migrate_dry_run` — no file written; report still produced
  - `test_migrate_cli_smoke` — `python -m harlo.migrate_path_c ...` invocation

## 5. Architect handoff to Forge

Forge implements `python/harlo/migrate_path_c.py` per §2 + tests per §4.

*End of Phase 4 migration design.*
