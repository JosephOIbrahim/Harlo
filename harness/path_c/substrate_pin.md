# Substrate Pin — `pyproject.toml [substrate]` extra

**Status:** Phase 0 Forge artifact &nbsp;|&nbsp; **Date:** 2026-04-28

## Pin

```toml
[project.optional-dependencies]
substrate = [
    "usd-core>=24.05",
]
```

## Resolved version

- **`usd-core==26.5`** (latest stable on PyPI as of pin date)
- Wheel: `usd_core-26.5-cp312-none-win_amd64.whl` (13.5 MB)
- Reports `Usd.GetVersion() == (0, 26, 5)` after install

## Rationale

- **PyPI source.** `usd-core` is the official Pixar OpenUSD distribution
  on PyPI. Pulls into `.venv312/Lib/site-packages/pxr/`.
- **Lower bound `>=24.05`.** First wheel cycle with stable Python 3.12
  support; chosen to give pip room to resolve newer minors without forcing
  the lock to the latest release.
- **No upper bound declared in this pin.** Could tighten later (e.g.
  `<27` or `<28`) once Phase 2 implementation reveals API surface
  dependencies. The codeless-schema authoring path Phase 1 follows is
  among the most stable USD APIs (`Sdf`, `Plug.Registry`,
  `Usd.SchemaRegistry`); unlikely to break across majors.
- **Vendored install untouched.** Sprint 4's `C:\USD\26.03-exec` install
  remains in place. `src/usd_bootstrap.py` continues to consume it via
  `sys.path` injection. The pip-installed `usd-core 26.5` in `.venv312`
  is the one Path C uses; the two do not interfere because Sprint 4
  modules are dormant (their import would short-circuit on the
  bootstrap path, and the bootstrap-imported `pxr` would resolve to
  whichever is found first in `sys.path` — pip-installed wins because
  site-packages is searched before bootstrap-prepended paths in
  practice).

## Install command and known issue

**Strict command per session gate criterion:**
```
.venv312/Scripts/python.exe -m pip install -e .[substrate]
```

**Status: BLOCKED on file lock**, not on pin. Maturin's editable build
succeeded (Rust compiled in 2.59s) but the copy of the freshly built
`hippocampus.dll` to `python/harlo/hippocampus.cp312-win_amd64.pyd`
failed:

```
Failed to copy C:\Users\User\Harlo\target\maturin\hippocampus.dll
to   C:\Users\User\Harlo\python\harlo\hippocampus.cp312-win_amd64.pyd
The process cannot access the file because it is being used by another process.
(os error 32)
```

Cause: another Python process on this machine has the `.pyd` loaded
(probably the MCP server or a still-running test process from a prior
session). The `.pyd` was already up-to-date prior to this Phase 0; the
maturin build was a no-op rebuild that the editable install requested
unnecessarily.

**Workaround used (Commandment 3, attempt 2 of 3):**
```
.venv312/Scripts/python.exe -m pip install "usd-core>=24.05"
```

Installs the substrate extra's only dependency directly into the venv,
bypassing the maturin rebuild that the existing on-disk artifact already
satisfies. Functionally equivalent for Phase 0's `import pxr` gate.

**Remediation (recommended for future Forge sessions):**
1. Identify the process holding the `.pyd` (`tasklist | findstr python`
   on Windows) and stop it cleanly.
2. Re-run `pip install -e .[substrate]` to formalize the editable
   install with the extra.
3. Alternatively, exclude the `.pyd` from the editable rebuild path
   (maturin `--skip-install` plus a manual `--editable` linking step).

This issue is a **Forge environment constraint, not a pin defect**.
Surface noted in `forge/mile_2_phase_0_report.md`. Crucible decides
whether it blocks the Phase 0 gate.

## Verification

```
$ .venv312/Scripts/python.exe -c "from pxr import Usd, Sdf, Plug; print(Usd.GetVersion())"
(0, 26, 5)
```

## Cross-references

- Decision authority: `harness/path_c/02_CONSTITUTION.md` Commandment 3,
  Law 3 (`pxr` install stays optional via `[substrate]` extra).
- Gate criterion: session override, "`pip install -e .[substrate]`
  succeeds in `.venv312`; `import pxr` works".
- Vendored alternative: `src/usd_bootstrap.py` — Sprint 4 path.

*End of substrate pin.*
